==============================================================================
  WEBHOOK-RELAY
  Recebe avisos de serviços externos e garante que cheguem ao destino.
  Feito por João Vitor (jota.) - joaotatanjo@gmail.com
==============================================================================


O QUE É ISSO
------------------------------------------------------------------------------
Quando alguém paga um Pix numa loja online, quem avisa a loja que o
pagamento caiu é um "webhook": o banco faz uma requisição para um endereço
da loja. Isso pode dar errado de três jeitos:

  1. Alguém finge ser o banco e manda um aviso falso.
     -> O relay confere uma assinatura secreta (HMAC) com horário.

  2. O sistema da loja está fora do ar quando o aviso chega.
     -> O relay guarda o aviso e tenta entregar de novo, esperando cada vez
        mais. Depois de 8 tentativas, manda para uma "fila morta".

  3. O banco manda o mesmo aviso duas vezes.
     -> O relay reconhece o aviso repetido e não entrega de novo.

Feito com: Python 3.12, FastAPI, Redis, PostgreSQL e Docker.


==============================================================================
  COMO RODAR NO SEU COMPUTADOR (WINDOWS)
==============================================================================

Este projeto tem várias partes funcionando juntas (API, workers, banco,
fila), então o jeito recomendado é com Docker.


JEITO 1 - COM DOCKER (recomendado: sobe tudo de uma vez)
------------------------------------------------------------------------------
1. Instale o Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Abra o Docker Desktop e espere ele ficar verde ("Engine running").
3. Abra a pasta webhook-relay no Explorador de Arquivos, clique com o botão
   direito num espaço vazio e escolha "Abrir no Terminal".
4. Rode:

       docker compose up --build

   Isso liga:
     - a API ............................ http://localhost:8000/docs
     - 2 workers (fazem as entregas)
     - o PostgreSQL (banco) e o Redis (fila)
     - um receptor de exemplo (porta 9000) que falha em 30% das vezes
       de propósito, para dar para ver as novas tentativas

5. Para desligar: Ctrl + C no terminal, e depois:

       docker compose down


JEITO 2 - SÓ OS TESTES, SEM DOCKER
------------------------------------------------------------------------------
Os testes automáticos usam um banco e uma fila "de mentira" na memória, então
rodam sem Docker. Precisa do Python 3.12 ou mais novo
(https://www.python.org/downloads/, marcando "Add python.exe to PATH").

Dentro da pasta webhook-relay:

       python -m venv .venv

       No PowerShell:  .venv\Scripts\activate
       No Git Bash:    source .venv/Scripts/activate

       pip install -r requirements-dev.txt
       pytest


==============================================================================
  TESTANDO DE PONTA A PONTA (com o Docker ligado)
==============================================================================

1. Abra http://localhost:8000/docs

2. Cadastre uma origem em  POST /sources

       {"name": "pagamentos"}

   COPIE o "secret" que aparecer. Ele só é mostrado agora.

3. Cadastre o receptor de exemplo como destino em  POST /destinations

       {"name": "receptor", "url": "http://receiver:9000/hook"}

4. Em OUTRO terminal, dentro da pasta webhook-relay, com o ambiente
   ativado (veja o Jeito 2), envie um aviso assinado:

       python examples/send_webhook.py --source pagamentos --secret COLE-O-SECRET-AQUI

   Tem que voltar "202" com o id do evento.

5. Acompanhe as tentativas de entrega:

       docker compose logs -f worker receiver

   Você vai ver algumas falhas (503) e depois a entrega com sucesso.

6. Veja o evento e cada entrega em  GET /events/{event_id}
   e a fila morta em  GET /deliveries


==============================================================================
  DEU ERRO?
==============================================================================

"docker não é reconhecido" ou "cannot connect to the Docker daemon"
   Abra o Docker Desktop e espere ele terminar de iniciar.

"port is already allocated"
   Algum programa já usa a porta 8000 ou 9000. Feche-o, ou rode
   docker compose down  e tente de novo.

O send_webhook.py responde 401
   O secret está errado. Cadastre outra origem e copie o secret novo.


==============================================================================
  ONDE FICA CADA COISA
==============================================================================

  app/signatures.py    assinatura HMAC com horário
  app/backoff.py       quanto esperar entre tentativas
  app/task_queue.py    fila no Redis (e uma versão em memória para testes)
  app/delivery.py      uma tentativa de entrega e o que fazer com o resultado
  app/worker.py        o programa que fica entregando os avisos
  app/routers/         as rotas da API
  examples/            script que envia aviso e receptor que falha de propósito
  tests/               testes automáticos


Licença: MIT
