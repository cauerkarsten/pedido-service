# pedido-service

Microsserviço de **pedidos** (FastAPI + PostgreSQL). Ao criar um pedido, ele reserva o produto no
estoque-service, do repositório do colega (padrão Saga); ao cancelar um pedido
confirmado, ele pede o estorno ao estoque (ação compensatória).

| Ambiente | Branch    | URL                                            | Estoque usado                      |
|----------|-----------|------------------------------------------------|------------------------------------|
| DEV      | `develop` | https://pedido-service-lzk8.onrender.com/docs  | https://estoque-dev-xraj.onrender.com   |
| HOMOL    | `main`    | https://pedido-homol-c247.onrender.com/health  | https://estoque-homol-e6on.onrender.com |

> O estoque-service fica no repositório do colega, com pipeline e deploy próprios.
> No Render grátis os serviços "dormem" sem uso: a primeira requisição pode levar cerca de
> 1 minuto. Abra as URLs antes de apresentar. Em HOMOL o Swagger fica desligado (`ENABLE_DOCS=false`).

## Endpoints

| Método | Rota                          | Descrição                                                   |
|--------|-------------------------------|-------------------------------------------------------------|
| GET    | `/health`                     | Verificação de saúde                                         |
| POST   | `/pedidos`                    | Cria o pedido e reserva no estoque (CONFIRMADO ou CANCELADO) |
| GET    | `/pedidos/{id}`               | Consulta um pedido                                           |
| PUT    | `/pedidos/{id}/cancelar`      | Cancela; se estava CONFIRMADO, estorna no estoque            |
| GET    | `/metrics`                    | Métricas no formato do Prometheus                            |
| GET    | `/docs`                       | Swagger (só quando `ENABLE_DOCS=true`)                       |

Se o estoque não responder, um pedido novo fica **CANCELADO**, e o cancelamento de um pedido
confirmado devolve **503** (o pedido continua CONFIRMADO para tentar de novo).

## Variáveis de ambiente

| Variável              | Padrão                                               | Descrição                                   |
|-----------------------|------------------------------------------------------|---------------------------------------------|
| `DATABASE_URL`        | `postgresql://admin_pedido:123@localhost:5433/pedido_db` | Conexão com o PostgreSQL                |
| `ESTOQUE_SERVICE_URL` | `http://localhost:8002`                              | Endereço do estoque-service                 |
| `ESTOQUE_TIMEOUT`     | `60`                                                 | Segundos esperando o estoque responder      |
| `ENABLE_DOCS`         | `true`                                               | Liga o Swagger (`false` em HOMOL)           |
| `PORT`                | `8000`                                               | Porta do servidor (o Render define sozinho) |

## Como rodar

**Com Docker** (sobe o pedido e um Postgres):

```bash
docker compose up --build
```

API em http://localhost:8003/docs. O estoque é procurado em `http://host.docker.internal:8002`;
para usar o estoque publicado, rode com `ESTOQUE_SERVICE_URL=https://estoque-dev-xraj.onrender.com`.

**Sem Docker** (Python 3.12):

```bash
python -m venv venv
venv\Scripts\activate          # Linux/Mac: source venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8003
```

**Testes** (usam SQLite em memória e simulam o estoque, não precisam de banco nem do estoque no ar):

```bash
pytest --cov=app
```

## Fluxo de branches

- `feature/*`: desenvolvimento. Abre PR para `develop`.
- `develop`: ambiente **DEV**. Cada merge publica no Render DEV.
- `main`: ambiente **HOMOL**. Recebe PR de `develop`; cada merge publica no Render HOMOL.
- Tags `vX.Y.Z` em `main`: versões publicadas no GHCR.

## Pipeline

```
feature/* ──PR──> develop ──PR──> main ──tag v1.0.0──> GHCR + Release
              │            │            │
             CI           CI + deploy  CI + deploy
                          Render DEV   Render HOMOL
```

1. **CI** ([.github/workflows/ci.yml](.github/workflows/ci.yml)), em todo push e PR:
   testes com cobertura (pytest), análise no **SonarCloud** e build da imagem Docker.
2. **Deploy** no **Render**: cada serviço acompanha uma branch (`develop` → DEV, `main` → HOMOL) e
   publica sozinho a cada push, só depois que o CI passa.
3. **Release** ([.github/workflows/release.yml](.github/workflows/release.yml)), ao enviar uma tag
   `v*.*.*`: roda os testes, publica a imagem em `ghcr.io/<usuario>/pedido-service` com as tags
   `X.Y.Z`, `X.Y` e `latest`, e cria a Release no GitHub com as notas geradas.
4. **Dependabot** ([.github/dependabot.yml](.github/dependabot.yml)): toda semana abre PRs para
   `develop` atualizando bibliotecas Python, actions e a imagem base do Docker.

### Como lançar uma versão

```bash
git checkout main
git pull
git tag v1.0.0
git push origin v1.0.0
```

A imagem fica em **Packages** no GitHub. Para rodar: `docker run -p 8000:8000 ghcr.io/<usuario>/pedido-service:1.0.0`.

Versionamento semântico: `MAJOR` quando quebra a API, `MINOR` para funcionalidade nova, `PATCH` para correção.

## Configuração inicial (uma vez)

**SonarCloud**
1. Em sonarcloud.io, importe este repositório.
2. Em *Administration → Analysis Method*, **desligue a Automatic Analysis** (a análise vem do CI).
3. Copie a organization e a project key para o [sonar-project.properties](sonar-project.properties).
4. Gere um token (*My Account → Security*) e cadastre no GitHub em
   *Settings → Secrets and variables → Actions* como `SONAR_TOKEN`.

**Render** (repetir para DEV e HOMOL)
1. *New → PostgreSQL* (plano Free): `pedido-db-dev` / `pedido-db-homol`.
2. *New → Web Service*, conecte o repositório, runtime **Docker**, branch `develop` (DEV) ou `main` (HOMOL).
3. Health check path: `/health`. Auto-Deploy: **After CI Checks Pass**.
4. Environment:
   - `DATABASE_URL` = *Internal Database URL* do Postgres criado no passo 1
   - `ESTOQUE_SERVICE_URL` = URL do estoque do mesmo ambiente
   - `ENABLE_DOCS` = `true` no DEV, `false` no HOMOL

**GitHub**
- *Settings → Branches*: proteja `main` e `develop` exigindo PR e o check **Testes e cobertura**.
- *Settings → Actions → General → Workflow permissions*: **Read and write** (para publicar no GHCR).

## Monitoramento

A pasta [observabilidade/](observabilidade/) tem Prometheus e Grafana monitorando os 4 serviços
(estoque e pedido, DEV e HOMOL) pelas URLs públicas do Render.

```bash
cd observabilidade
docker compose up -d
```

- Prometheus: http://localhost:9090 (*Status → Targets* mostra se os 4 estão `UP`)
- Grafana: http://localhost:3000 (admin / admin). O dashboard **Microsserviços - Estoque e Pedido**
  já vem carregado, com os gráficos de requisições por segundo, latência p95 e erros 5xx, e um
  filtro por serviço/ambiente no topo.

Os targets dos 4 serviços estão em
[observabilidade/prometheus/prometheus.yml](observabilidade/prometheus/prometheus.yml).
Os dois serviços expõem `/metrics` com a mesma biblioteca (`prometheus-fastapi-instrumentator`).

**Sem Docker** (máquina sem virtualização): baixe os binários para Windows do
[Prometheus](https://prometheus.io/download/) e do [Grafana](https://grafana.com/grafana/download?platform=windows)
e use os mesmos arquivos desta pasta:

```bash
prometheus.exe --config.file=observabilidade/prometheus/prometheus.yml
```

No Grafana, aponte `[paths] provisioning` para uma cópia de `observabilidade/grafana/provisioning/`
com a URL do datasource trocada para `http://localhost:9090` e o caminho dos dashboards para
`observabilidade/grafana/dashboards`.

**O que cada gráfico mede:**

| Gráfico | Consulta (PromQL) |
|---------|-------------------|
| Serviço no ar | `up` (1 quando o Prometheus consegue ler o `/metrics`) |
| Requisições por segundo | `sum by (job) (rate(http_requests_total[1m]))` |
| Latência p95 | `histogram_quantile(0.95, sum by (job, le) (rate(http_request_duration_highr_seconds_bucket[5m])))` |
| Erros 5xx por segundo | `sum by (job) (rate(http_requests_total{status="5xx"}[5m]))` |

> Enquanto o Prometheus estiver rodando, ele consulta os serviços a cada 15 s e impede que eles
> durmam, o que consome as 750 h/mês grátis do Render. Desligue com `docker compose down` depois.

> **Segurança:** aqui o `/metrics` é público, o que é aceitável para um trabalho acadêmico. Em
> produção ele ficaria protegido (rede interna, autenticação ou allowlist de IP do Prometheus).
