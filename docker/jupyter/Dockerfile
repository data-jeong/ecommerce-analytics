FROM jupyter/pyspark-notebook:latest

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER $NB_UID

# Install Python packages
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install Jupyter Lab extensions
RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager \
    && jupyter labextension install @jupyterlab/git \
    && jupyter labextension install @jupyterlab/toc

# Set working directory
WORKDIR /home/jovyan/work

# Copy notebooks
COPY notebooks/ /home/jovyan/notebooks/

# Expose port
EXPOSE 8888

# Start Jupyter Lab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''"] 