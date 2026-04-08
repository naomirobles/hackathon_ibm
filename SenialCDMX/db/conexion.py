import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(
        "postgresql://neondb_owner:npg_li1jHAb2UXdg@ep-morning-queen-am4dvig4-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require",
        sslmode="require"
    )
