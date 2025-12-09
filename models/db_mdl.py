# models/db_mdl.py
import uuid
import random
import string
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from contextlib import contextmanager
from urllib.parse import quote

# ----------------------------------------------------
# Configuración de la Base de Datos
# ----------------------------------------------------
DATABASE_USER = "dbflaskinacap"
DATABASE_PASSWD = quote("1N@C@P_alumn05")
DATABASE_HOST = "mysql.flask.nogsus.org"
DATABASE_NAME = "api_alumnos"
DATABASE_URL = f"mysql+pymysql://{DATABASE_USER}:{DATABASE_PASSWD}@{DATABASE_HOST}/{DATABASE_NAME}"

engine = create_engine(DATABASE_URL)
Base = declarative_base()


# ----------------------------------------------------
# Modelos con nombres de tablas corregidos
# ----------------------------------------------------
class Usuario(Base):
    __tablename__ = 'lfsh_usuario'

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(Text(100000), index=True)
    apellido = Column(String(150), index=True)
    usuario = Column(String(50), index=True)
    clave = Column(String(50), index=True)
    api_key = Column(String(250), index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "usuario": self.usuario,
            "api_key": self.api_key
        }


class Mercado(Base):
    __tablename__ = 'lfsh_mercados'

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), index=True)


class Producto(Base):
    __tablename__ = 'lfsh_productos'

    id = Column(Integer, primary_key=True, index=True)
    idOrigen = Column(Integer, ForeignKey('lfsh_mercados.id'), nullable=False, index=True)
    nombre = Column(String(150), index=True)
    uMedida = Column(String(100), index=True)
    precio = Column(Integer, index=True)

    mercado = relationship("Mercado")

    def to_dict(self):
        mercado_nombre = self.mercado.nombre if self.mercado else None
        return {
            "id": self.id,
            "idOrigen": self.idOrigen,
            "nombre": self.nombre,
            "uMedida": self.uMedida,
            "precio": self.precio,
            "mercado_nombre": mercado_nombre
        }


# ----------------------------------------------------
# Sesiones de base de datos
# ----------------------------------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# ----------------------------------------------------
# Funciones de utilidad
# ----------------------------------------------------
def generar_captcha():
    caracteres = string.ascii_uppercase + string.digits
    return ''.join(random.choice(caracteres) for _ in range(6))


def generar_api_key():
    return f"lfsh_{uuid.uuid4().hex}"


def valida_usuario(usrname, passwd):
    try:
        with get_db() as db:
            user = db.query(Usuario).filter(
                Usuario.usuario == usrname,
                Usuario.clave == passwd
            ).first()

            if user:
                user.api_key = generar_api_key()
                db.commit()
                db.refresh(user)
                return user
            return None
    except Exception as e:
        print(f"Error en valida_usuario: {e}")
        return None


def verificar_api_key(api_key):
    try:
        with get_db() as db:
            user = db.query(Usuario).filter(Usuario.api_key == api_key).first()
            return user is not None
    except Exception as e:
        print(f"Error en verificar_api_key: {e}")
        return False