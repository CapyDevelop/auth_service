import logging
import os
import time
import uuid

import auth_service.authservice_pb2 as auth_pb2
import auth_service.authservice_pb2_grpc as auth_pb2_grpc
import db_service.db_handler_pb2 as db_pb2
import db_service.db_handler_pb2_grpc as db_pb2_grpc
import grpc
import school_service.school_service_pb2 as school_pb2
import school_service.school_service_pb2_grpc as school_pb2_grpc
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

db_service_channel = grpc.insecure_channel(
    f'{os.getenv("DB_SERVICE_HOST")}:{os.getenv("DB_SERVICE_PORT")}'
)
db_service_stub = db_pb2_grpc.DBServiceStub(db_service_channel)

school_service_channel = grpc.insecure_channel(
    f'{os.getenv("SCHOOL_GRPC_HOST")}:{os.getenv("SCHOOL_GRPC_PORT")}'
)
school_service_stub = school_pb2_grpc.SchoolServiceStub(school_service_channel)


class AuthService(auth_pb2_grpc.AuthServiceServicer):
    def login(self, request, context):
        logging.info("Receive request from client")
        logging.info("Start request to rRPC server")
        user_info_request = \
            school_pb2.GetSchoolRequest(username=request.username,
                                        password=request.password)
        user_info_response = school_service_stub.get_school_info(user_info_request)
        logging.info(f"Receive response from rRPC server")
        logging.info(f"school user id: {user_info_response.school_user_id}")
        if not user_info_response.access_token:
            logging.info(f"Error response from gRPC server")
            return auth_pb2.LoginResponse(
                description=user_info_response.description,
                status=5,
                uuid="None"
            )
        logging.info(f"Success response from gRPC server")
        logging.info("Check user exists")
        check_user_exist_request = db_pb2.CheckUserExistsRequest(
            school_user_id=user_info_response.school_user_id
        )
        check_user_exist_response = db_service_stub.check_user_exists(check_user_exist_request)
        if not check_user_exist_response.exists:
            logging.info("User not exists")
            logging.info("Create user")
            logging.info("Check capybara")
            if user_info_response.coalition == " Capybaras":
                logging.info("Capybara")
                capy_uuid = str(uuid.uuid4())
                create_user_request = db_pb2.SetNewUserRequest(school_user_id=user_info_response.school_user_id,
                                                               access_token=user_info_response.access_token,
                                                               refresh_token=user_info_response.refresh_token,
                                                               session_state=user_info_response.session_state,
                                                               expires_in=user_info_response.expires_in,
                                                               uuid=capy_uuid)
                create_user_response = db_service_stub.set_new_user(create_user_request)
                if create_user_response.status != 0:
                    logging.info("Error create user")
                    return auth_pb2.LoginResponse(
                        description=create_user_response.description,
                        status=6,
                        uuid="None"
                    )
                logging.info("Success create user")
                return auth_pb2.LoginResponse(
                    description="Success",
                    status=0,
                    uuid=capy_uuid
                )
            return auth_pb2.LoginResponse(
                description="Увы, Вы не являетесь капибарой",
                status=2,
                uuid="None"
            )
        set_info_request = db_pb2.SetAccessDataRequest(school_user_id=user_info_response.school_user_id,
                                                       access_token=user_info_response.access_token,
                                                       refresh_token=user_info_response.refresh_token,
                                                       session_state=user_info_response.session_state,
                                                       expires_in=user_info_response.expires_in)
        set_info_response = db_service_stub.set_access_data(set_info_request)
        uuid_request = db_pb2.GetUUIDRequest(school_user_id=user_info_response.school_user_id)
        uuid_response = db_service_stub.get_uuid(uuid_request)
        if uuid_response.uuid == "None":
            return auth_pb2.LoginResponse(
                description="Error handler api",
                status=6,
                uuid="None"
            )
        return auth_pb2.LoginResponse(
            description="Success",
            status=0,
            uuid=uuid_response.uuid
        )

    def get_token_by_uuid(self, request, context):
        db_request = db_pb2.GetAccessTokenByUUIDRequest(uuid=request.uuid)
        db_response = db_service_stub.get_access_token_by_uuid(db_request)
        print(db_response.status)
        if db_response.status != 0:
            return auth_pb2.TokenResponse(
                description=db_response.description,
                status=db_response.status
            )
        print(db_response.time_create + db_response.expires_in)
        print(int(time.time()))
        if (db_response.time_create + db_response.expires_in) > int(time.time()):
            print("Token expired")
            return auth_pb2.TokenResponse(
                description="Token expired",
                status=1
            )
        return auth_pb2.TokenResponse(
            description="Success",
            status=0,
            access_token=db_response.access_token
        )
