FROM us-docker.pkg.dev/deeplearning-platform-release/gcr.io/workbench-container:latest

WORKDIR /opt/my-custom-env

COPY . .

RUN ls -lah /opt/my-custom-env

# Move files back to /home/jupyter when the container starts
CMD cp -r /opt/my-custom-env/* /home/jupyter/ && /run_jupyter.sh
