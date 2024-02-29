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

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - '
                           '%(levelname)s - %(message)s')
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
        logging.info("[ LOGIN ] Start request. ----- START -----")
        logging.info("[ LOGIN ] Start request to school_service (get_school_info)")
        user_info_request = \
            school_pb2.GetSchoolRequest(username=request.username,
                                        password=request.password)
        user_info_response = school_service_stub.get_school_info(user_info_request)
        logging.info("[ LOGIN ] Receive response from school_service (get_school_info)")
        if not user_info_response.access_token:
            logging.info("[ LOGIN ] Error response from school_server (get_school_info)")
            return auth_pb2.LoginResponse(
                description=user_info_response.description,
                status=5,
                uuid="None"
            )
        logging.info(f"[ LOGIN ] School user id: {user_info_response.school_user_id}")
        logging.info("[ LOGON ] Check user exists. request to db_service (check_user_exists)")
        check_user_exist_request = db_pb2.CheckUserExistsRequest(
            school_user_id=user_info_response.school_user_id
        )
        check_user_exist_response = db_service_stub.check_user_exists(check_user_exist_request)
        if not check_user_exist_response.exists:
            logging.info("[ LOGIN ]\t\tUser not exists. Create user. Check CAPYBARA")
            # if user_info_response.coalition == "Capybaras" or request.username in ["ccamie@student.21-school.ru"]:
            logging.info("[ LOGIN ]\t\tStudent!")
            capy_uuid = str(uuid.uuid4())
            create_user_request = db_pb2.SetNewUserRequest(school_user_id=user_info_response.school_user_id,
                                                           access_token=user_info_response.access_token,
                                                           refresh_token=user_info_response.refresh_token,
                                                           session_state=user_info_response.session_state,
                                                           expires_in=user_info_response.expires_in,
                                                           uuid=capy_uuid)
            create_user_response = db_service_stub.set_new_user(create_user_request)
            if create_user_response.status != 0:
                logging.info(f"[ LOGIN ]\t\tError create user. uuid:{capy_uuid}. ----- END -----")
                return auth_pb2.LoginResponse(
                    description=create_user_response.description,
                    status=6,
                    uuid="None"
                )
            logging.info(f"[ LOGIN ]\t\tSuccess create user. uuid:{capy_uuid}. ----- END -----")
            return auth_pb2.LoginResponse(
                description="Success",
                status=0,
                uuid=capy_uuid
            )
            # logging.info("[ LOGIN ]\t\tNot capybara. ----- END -----")
            # return auth_pb2.LoginResponse(
            #     description="Увы, Вы не являетесь капибарой",
            #     status=2,
            #     uuid="None"
            # )
        logging.info("[ LOGIN ] User exists. Start request to db_service (set_access_data)")
        set_info_request = db_pb2.SetAccessDataRequest(school_user_id=user_info_response.school_user_id,
                                                       access_token=user_info_response.access_token,
                                                       refresh_token=user_info_response.refresh_token,
                                                       session_state=user_info_response.session_state,
                                                       expires_in=user_info_response.expires_in)
        set_info_response = db_service_stub.set_access_data(set_info_request)
        logging.info("[ LOGIN ] Receive response from db_service (set_access_data)")
        if set_info_response.status != 0:
            logging.info("[ LOGIN ] Error response from db_service (set_access_data). ----- END -----")
            return auth_pb2.LoginResponse(
                description=set_info_response.description,
                status=6,
                uuid="None"
            )
        logging.info("[ LOGIN ] Success response from db_service (get_uuid)")
        uuid_request = db_pb2.GetUUIDRequest(school_user_id=user_info_response.school_user_id)
        uuid_response = db_service_stub.get_uuid(uuid_request)
        if uuid_response.uuid == "None":
            logging.info("[ LOGIN ] Error response from db_service (get_uuid). ----- END -----")
            return auth_pb2.LoginResponse(
                description="Error handler api",
                status=6,
                uuid="None"
            )
        logging.info("[ LOGIN ] Success response from db_service (get_uuid). ----- END -----")
        return auth_pb2.LoginResponse(
            description="Success",
            status=0,
            uuid=uuid_response.uuid
        )

    def get_token_by_uuid(self, request, context):
        logging.info("[ GET TOKEN BY UUID ] Start request to db_service (get_access_token_by_uuid). ----- START -----")
        logging.info(f"[ GET TOKEN BY UUID ] UUID: {request.uuid}")
        db_request = db_pb2.GetAccessTokenByUUIDRequest(uuid=request.uuid)
        db_response = db_service_stub.get_access_token_by_uuid(db_request)
        if db_response.status != 0:
            logging.info("[ GET TOKEN BY UUID ] "
                         "Error response from db_service (get_access_token_by_uuid). ----- END -----")
            return auth_pb2.TokenResponse(
                description=db_response.description,
                status=db_response.status
            )
        logging.info("[ GET TOKEN BY UUID ] Check token expired")
        if (db_response.time_create + db_response.expires_in) < int(time.time()):
            logging.info("[ GET TOKEN BY UUID ] Token expired. ----- END -----")
            return auth_pb2.TokenResponse(
                description="Token expired",
                status=13
            )
        logging.info("[ GET TOKEN BY UUID ] Token OK. ----- END -----")
        return auth_pb2.TokenResponse(
            description="Success",
            status=0,
            access_token=db_response.access_token
        )
