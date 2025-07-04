import os
import asyncio
from dotenv import load_dotenv




def iniciar_aplicacion():
    print("Hola, tu aplicación ha comenzado a ejecutarse.")
    print("-----------------*----------------------")
    inputurl = input("Introduce la URL que quieras auditar: ")
    inputsearchconsole = input("Introduce las credenciales de search console: ")
    inputanalytics = input("Introduce las credenciales de analytics: ")
    load_dotenv(override=True)










if __name__ == "__main__":
    iniciar_aplicacion()