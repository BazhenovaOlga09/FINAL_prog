HOME_DIR = '/home/student/FINAL_prog'
LOGS = f'{HOME_DIR}/logs.txt'
DB_FILE = f'{HOME_DIR}/users.db'


IAM_TOKEN_PATH = f'{HOME_DIR}/creds/iam_token.txt'
FOLDER_ID_PATH = f'{HOME_DIR}/creds/folder_id.txt'
BOT_TOKEN_PATH = f'{HOME_DIR}/creds/bot_token.txt'



MAX_USER_STT_BLOCKS = 4
MAX_USER_TTS_SYMBOLS = 800
MAX_TTS_SYMBOLS = 500
MAX_USER_GPT_TOKENS = 500
MAX_GPT_TOKENS = 120
MAX_USERS = 3


SYSTEM_PROMPT = [{'role': 'system', 'text': 'Ты веселый собеседник. Общайся с пользователем на "вы". '
                                            'Поддерживай диалог. Не объясняй пользователю, что ты умеешь и можешь. '
                                            'Изображай человека. Отвечай кратко, максимум 3 предложения'}]