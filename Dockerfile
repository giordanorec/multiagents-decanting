# mad (MultiAgent Decanting) — imagem para CI, ambientes locked-down ou Codespaces.
# Roda a CLI do mad (init/doctor/dashboard/...). O Claude Code em si não vai aqui;
# esta imagem serve o scaffold, o doctor e o dashboard de forma isolada.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ scripts/
COPY templates/ templates/
COPY agents/ agents/
COPY dashboard/ dashboard/
COPY hooks/ hooks/
COPY locale/ locale/
COPY bin/ bin/

EXPOSE 8765 9765

ENTRYPOINT ["python", "scripts/mad.py"]
CMD ["version"]
