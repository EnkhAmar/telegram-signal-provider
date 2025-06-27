FROM public.ecr.aws/lambda/python:3.12

# Install required system packages
# RUN dnf install -y \
#     tar \
#     xz \
#     mesa-libGL \
#     libSM \
#     libXrender \
#     libXext && \
#     dnf clean all && \
#     rm -rf /var/cache/dnf

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}
COPY .env ${LAMBDA_TASK_ROOT}

# Install Python packages
# RUN pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu
# RUN pip install ultralytics==8.3.89
RUN pip install -r requirements.txt

# Copy function code and assets
COPY trade.py ${LAMBDA_TASK_ROOT}

# Lambda function entry point
CMD [ "trade.handler" ]

# aws ecr create-repository --profile amarhan --repository-name binance-handler --region ap-northeast-2 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
# docker buildx build --platform linux/amd64 --provenance=false -t binance-handler:latest .