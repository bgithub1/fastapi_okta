'''
Created on Nov 21, 2021

@author: bperlman1
'''
import uvicorn
from typing import Optional,List,Dict
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
import httpx
from starlette.config import Config
from okta_jwt.jwt import validate_token as validate_locally

class Item(BaseModel):
    name: str
    price: float
    is_offer: Optional[bool] = None

# Call the Okta API to get an access token
# def retrieve_token(authorization, issuer, scope='items'):
def retrieve_token(authorization, issuer, scope='fastapi'):
    headers = {
        'accept': 'application/json',
        'authorization': authorization,
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials',
        'scope': scope,
    }
    url = issuer + '/v1/token'

    response = httpx.post(url, headers=headers, data=data)

    if response.status_code == httpx.codes.OK:
        return response.json()
    else:
        raise HTTPException(status_code=400, detail=response.text)


def validate_remotely(token, issuer, clientId, clientSecret):
    headers = {
        'accept': 'application/json',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
    }
    data = {
        'client_id': clientId,
        'client_secret': clientSecret,
        'token': token,
    }
    url = issuer + '/v1/introspect'

    response = httpx.post(url, headers=headers, data=data)

    return response.status_code == httpx.codes.OK and response.json()['active']

# Validate the token
# Define the auth scheme and access token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
def validate(token: str = Depends(oauth2_scheme)):
    config = Config('./temp_folder/.env')
#     res = validate_remotely(
#         token,
#         config('OKTA_ISSUER'),
#         config('OKTA_CLIENT_ID'),
#         config('OKTA_CLIENT_SECRET')
#     )

    res = validate_locally(
        token,
        config('OKTA_ISSUER'),
        config('OKTA_AUDIENCE'),
        config('OKTA_CLIENT_ID')
    )
 
    if res:
        return True
    else:
        raise HTTPException(status_code=400)

class ItemStorage(BaseModel):
    dict_items:Dict[int,Item] = {
            0:Item(name='bill',price=12.00,is_offer=True),
            1:Item(name='sarah',price=14.00,is_offer=False)
            }
        
    
    def get_item(self,item_id:int):
        return self.dict_items[item_id]

    def put_item(self,item_id:int,item:Item):
        self.dict_items[item_id] = item

item_db = ItemStorage()

def add_routes(app):
    
    @app.get("/")
    def read_root():
        return {"Hello": "World of Items"}
    
    
    @app.get("/items/{item_id}")
    def read_item(
            item_id: int, 
            q: Optional[str] = None,
            valid: bool = Depends(validate)
        ):
        r = item_db.get_item(item_id)
        return {"item_id": item_id, "q": q,"returned_item":r}
    
    
    @app.post("/add/")
    async def add_item(item: Item,valid: bool = Depends(validate)):
        print(item)
        item_id = max(item_db.dict_items.keys())+1
        item_db.put_item(item_id, item)
        return item_db.get_item(item_id)
    
    @app.post("/update/")
    async def updage_item(item_id:int,item: Item,valid: bool = Depends(validate)):
        item_db.put_item(item_id, item)
        return item_db.get_item(item_id)
    
    # Get auth token endpoint
    @app.post('/token')
    def login(request: Request):
        # Load environment variables
        config = Config('./temp_folder/.env')
        return retrieve_token(
            request.headers['authorization'],
            config('OKTA_ISSUER'),
#             'all_items'
            'fastapi'
        )
    # Protected, get items route
    @app.get('/all_items', response_model=List[Item])
    def read_items(valid: bool = Depends(validate)):
        r = [Item.parse_obj(v) for v in item_db.dict_items.values()]
        return r
#         return [
#             Item.parse_obj({'id': 1, 'name': 'red ball'}),
#             Item.parse_obj({'id': 2, 'name': 'blue square'}),
#             Item.parse_obj({'id': 3, 'name': 'purple ellipse'}),
#         ]

if __name__=='__main__':
    myapp =FastAPI()
    add_routes(myapp)
    # Define the auth scheme and access token URL    
    uvicorn.run(myapp, port=4500)

    
    