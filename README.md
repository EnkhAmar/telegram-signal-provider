# telegram-signal-provider

```
pm2 start signal_listener.py --interpreter /home/ubuntu/telegram-signal-provider/env/bin/python3
```

sudo pm2 start echo.py --interpreter=/home/ubuntu/telegram-signal-provider/env/bin/python3


```
sudo pm2 start /home/ubuntu/telegram-signal-provider/signal_listener.py \
  --interpreter /home/ubuntu/telegram-signal-provider/env/bin/python3 \
  --name signal_listener
```


```bash
aws ecr get-login-password --profile amarhan --region ap-northeast-2 | docker login --username AWS --password-stdin 549378813718.dkr.ecr.ap-northeast-2.amazonaws.com
```


```bash
aws ecr create-repository --profile amarhan --repository-name binance-handler --region ap-northeast-2 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
```

```bash
docker buildx build --platform linux/amd64 --provenance=false -t binance-handler:latest .
```

```bash
docker tag binance-handler:latest 549378813718.dkr.ecr.ap-northeast-2.amazonaws.com/binance-handler:latest
```

```bash
docker push 549378813718.dkr.ecr.ap-northeast-2.amazonaws.com/binance-handler:latest
```