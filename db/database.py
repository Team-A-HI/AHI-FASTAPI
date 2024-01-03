from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from configset.config import *

# 1. SQLAlchemy 용 DB URL 생성
dburl = geturl()

# mysql db에 연결
SQLALCHEMY_DATABASE_URL = f"{dburl}"

# 2. 첫 번째 단계는 SQLAlchemy "엔진"을 만드는 것입니다.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,echo=True
)

metadata_obj = MetaData()
metadata_obj.bind = engine

# 3. Make SessionLocal class
# 생성한 SQLAlchemy engine 을 물려서(?) 세션을 생성합니다.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()

# 4. Base class 생성
# Base = declarative_base()

# 5. db에서 데이터 조회를 해서 skill 정보를 리턴한다.
def findPosting(findCode):
    SkillTable = Table("skill", metadata_obj, autoload_with=engine)

    # posting_code에 해당하는 skill 레코드 조회
    skill_stmt = select(SkillTable).where(SkillTable.c.posting_code == findCode)
    skill_result = db.execute(skill_stmt).fetchone()

    if skill_result:
        # skill_code 반환
        skill_name = skill_result.skill_name
        db.close()
        return skill_name
    else:
        db.close()
        return '정보 없음'

# # 조회
# stmt = select(some_table)
# datas = SessionLocal.execute(stmt)
# for data in datas:
#     print(data)

# # 입력
# stmt = insert(some_table).values()
# SessionLocal.execute(stmt)
# SessionLocal.commit()
