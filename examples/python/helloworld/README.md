[This code's documentation lives on the grpc.io site.](https://grpc.io/docs/languages/python/quickstart)

```bash
$ python -m grpc_tools.protoc -I../../protos --python_out=. --grpc_python_out=. ../../protos/health.proto
$ python -m grpc_tools.protoc -I../../protos --python_out=. --grpc_python_out=. ../../protos/helloworld.proto
```
