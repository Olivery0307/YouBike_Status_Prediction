# Use the official AWS Lambda Python 3.11 base image
FROM public.ecr.aws/lambda/python:3.11

# Copy the requirements file into the image
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install build dependencies
RUN yum install -y gcc gcc-c++ && yum clean all

# Install the dependencies
RUN pip install -r requirements.txt

# Copy your prediction script into the image
COPY prediction_lambda.py ${LAMBDA_TASK_ROOT}/

# Set the command to run your function's handler
CMD [ "prediction_lambda.lambda_handler" ]