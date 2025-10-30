FROM registry.access.redhat.com/ubi9/python-311:latest

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    PORT=8501

WORKDIR /opt/app-root/src

COPY --chown=1001:0 . /opt/app-root/src

RUN pip install --no-cache-dir streamlit==1.50.0

EXPOSE 8501

USER 1001

CMD ["sh", "-c", "streamlit run family_feud_streamlit.py --server.address=0.0.0.0 --server.port=${PORT}"]