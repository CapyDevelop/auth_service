import logging
import os
from concurrent import futures

import auth_service.authservice_pb2_grpc as auth_pb2_grpc
import grpc
from dotenv import load_dotenv

from capybara_auth_service import AuthService

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthService(), server)
    server.add_insecure_port(f'[::]:{os.getenv("AUTH_PORT")}')
    logging.info(f"Start server on port {os.getenv('AUTH_PORT')}")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
