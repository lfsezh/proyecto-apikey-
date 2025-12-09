# app.py
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'  # Previene creación de .pyc

from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from routes.routes import rutas
from models.db_mdl import get_db, Usuario, valida_usuario, generar_captcha
import functools

app = Flask(__name__, template_folder='templates')
app.secret_key = 'lfsh_sistema_seguro_2025'
app.register_blueprint(rutas, url_prefix="/api")

# ========== CONFIGURACIÓN PARA DESACTIVAR CACHE ==========
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# Decorador para requerir API Key
def requiere_api_key(f):
    @functools.wraps(f)
    def decorador(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        from models.db_mdl import verificar_api_key
        if not api_key or not verificar_api_key(api_key):
            return jsonify({"error": "API Key inválida o no proporcionada"}), 401
        return f(*args, **kwargs)

    return decorador


@app.route("/")
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        # Generar captcha para la sesión
        captcha = generar_captcha()
        session['captcha'] = captcha
        return render_template("login.html", captcha=captcha)

    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        captcha_input = request.form.get("captcha", "").upper()
        captcha_session = session.get('captcha', '')

        # Validar captcha
        if not captcha_input or captcha_input != captcha_session:
            captcha = generar_captcha()
            session['captcha'] = captcha
            return render_template("login.html",
                                   message=" !! NO NO NO ¡¡ Código de seguridad incorrecto",
                                   captcha=captcha)

        # Validar usuario
        dtUsr = valida_usuario(username, password)

        if dtUsr:
            session['user_id'] = dtUsr.id
            session['username'] = dtUsr.usuario
            session['api_key'] = dtUsr.api_key
            session['nombre'] = f"{dtUsr.nombre} {dtUsr.apellido}"
            return redirect(url_for('dashboard'))
        else:
            captcha = generar_captcha()
            session['captcha'] = captcha
            return render_template("login.html",
                                   message="Usuario o contraseña incorrectos",
                                   captcha=captcha)


@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template("dashboard.html",
                           nombre=session.get('nombre'),
                           api_key=session.get('api_key'))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route("/usuario", methods=["GET"])
@requiere_api_key
def usuario():
    """Endpoint para obtener información del usuario con API Key"""
    try:
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        with get_db() as db:
            user = db.query(Usuario).filter(Usuario.api_key == api_key).first()
            if user:
                return jsonify(user.to_dict())
            return jsonify({"error": "Usuario no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Endpoint de prueba sin API Key (solo para debug)
@app.route("/test", methods=["GET"])
def test():
    return jsonify({"status": "ok", "message": "API Flask funcionando"})


# ========== MIDDLEWARE PARA ELIMINAR CACHE EN HEADERS ==========
@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 0 minutes.
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


if __name__ == '__main__':
    # Forzar recarga en modo desarrollo
    app.run(debug=True, use_reloader=True, host='0.0.0.0', port=5000)