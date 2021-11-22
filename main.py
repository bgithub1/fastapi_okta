'''
Created on Nov 20, 2021

@author: bperlman1
'''

import pandas as pd

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import io

app = FastAPI()


# Hello World route
@app.get("/")
def read_root():
    df = pd.read_csv('prop_bets_nhl_will_score.csv')
    stream = io.StringIO()
    
    df.to_csv(stream, index = False)
    
    response = StreamingResponse(iter([stream.getvalue()]),
                         media_type="text/csv"
    )
    
    response.headers["Content-Disposition"] = "attachment; filename=export.csv"
    
    return response