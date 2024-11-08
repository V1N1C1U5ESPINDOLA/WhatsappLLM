import psycopg2
from langchain_openai import OpenAI  
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from twilio.rest import Client
import os

load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')
twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone = f"whatsapp:{os.getenv('TWILIO_PHONE_NUMBER')}"
user_phone = f"whatsapp:{os.getenv('USER_PHONE_NUMBER')}"

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

llm = OpenAI(openai_api_key=openai_api_key, temperature=0.1)
template = """
Converta o seguinte texto em uma consulta SQL. Considere as seguintes tabelas:
- `pacientes` com colunas `id`, `nome`, `data_nascimento`
- `agendamentos` com colunas `id`, `paciente_id` (FK para `pacientes.id`), `data_agendamento`, `hora_agendamento`
- `comparecimento` com colunas `id`, `agendamento_id` (FK para `agendamentos.id`), `compareceu` (BOOLEAN), `data_comparecimento`

Instrucao: {text}
"""
prompt = PromptTemplate(input_variables=["text"], template=template)
chain = prompt | llm

client = Client(twilio_sid, twilio_auth_token)

def text_to_sql(text):
    print("Buscando informacoes no banco de dados ...\n")
    try:
        sql_query = chain.invoke(text)
        print("Consulta SQL ^-^ :\n{",sql_query,"\n}\n")
        
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        formatted_results = []
        for row in results:
            formatted_row = "\t".join(str(value) for value in row)
            formatted_results.append(formatted_row)
        formatted_output = "\n".join(formatted_results)
        
        try:
            message = client.messages.create(
                body=f"Resultado da consulta:\n{formatted_output}",
                from_=twilio_phone,
                to=user_phone
            )
            print(f"Mensagem enviada com sucesso! SID da mensagem: {message.sid}")
        except Exception as e:
            print(f"Erro ao enviar a mensagem: {e}")
        
        return formatted_output
    except psycopg2.Error as db_error:
        return f"Erro no banco de dados >.< : {db_error}"
    except Exception as e:
        return f"Erro ao gerar a consulta ;-; : {e}"

prompt_text = input("O que voce gostaria de saber acerca dos pacientes? \n")
results = text_to_sql(prompt_text)
print("Resposta:\n", results)

cursor.close()
conn.close()