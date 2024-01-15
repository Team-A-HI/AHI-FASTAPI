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


def findPosting(search_Code):
    SkillTBL = Table("skill", metadata_obj, autoload_with=engine)
    
    stmt = select(SkillTBL).where(SkillTBL.c.posting_code == search_Code)
# 3. Make SessionLocal class
    with engine.connect() as connection:
        results = connection.execute(stmt).fetchall()
# 4. skill_names 가져온다
    skill_names = [result.skill_name for result in results]
    if skill_names == null:
        skill_names = "공고가 없습니다"
        return skill_names
# 5. db에서 데이터 조회를 해서 skill 정보를 리턴한다.
    return skill_names


# user의 이력서 정보를 가져온다
def findResume(userData):
    FileTBL = Table("file", metadata_obj, autoload_with=engine)
    stmt = select(FileTBL).where(FileTBL.c.posting_code == userData)

    with engine.connect() as connection:
        results = connection.execute(stmt).fetchall()

    file_names = []
    
    return file_names

# # 조회
# stmt = select(some_table)
# datas = SessionLocal.execute(stmt)
# for data in datas:
#     print(data)

# # 입력
# stmt = insert(some_table).values()
# SessionLocal.execute(stmt)
# SessionLocal.commit()
