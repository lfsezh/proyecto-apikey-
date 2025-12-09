# routes/routes.py
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from models.db_mdl import get_db, Producto, Mercado, verificar_api_key
import functools

rutas = Blueprint("rutas", __name__)


# Decorador para proteger endpoints
def requiere_api_key(f):
    @functools.wraps(f)
    def decorador(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if not api_key or not verificar_api_key(api_key):
            return jsonify({"error": "API Key inválida o no proporcionada"}), 401
        return f(*args, **kwargs)

    return decorador


# GET /api/productos - Listar todos los productos con nombre de mercado
@rutas.route("/productos", methods=["GET"])
@requiere_api_key
def listar_productos():
    """Listar productos incluyendo el nombre de su mercado"""
    try:
        with get_db() as db:
            # Obtener parámetros de paginación (opcionales)
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)

            # Calcular offset
            offset = (page - 1) * per_page

            # Consulta con join para obtener el nombre del mercado
            query = db.query(Producto).join(Mercado, Producto.idOrigen == Mercado.id)
            total = query.count()

            productos = query.offset(offset).limit(per_page).all()

            resultado = []
            for p in productos:
                prod_dict = {
                    "id": p.id,
                    "nombre": p.nombre,
                    "idOrigen": p.idOrigen,
                    "uMedida": p.uMedida,
                    "precio": p.precio,
                    "mercado": p.mercado.nombre if p.mercado else None
                }
                resultado.append(prod_dict)

            return jsonify({
                "status": "success",
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
                "productos": resultado
            }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# POST /api/productos - Insertar un producto (requiere idOrigen)
@rutas.route("/productos", methods=["POST"])
@requiere_api_key
def crear_producto():
    """Crear un nuevo producto"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No se proporcionó datos JSON"}), 400

    campos_requeridos = ['nombre', 'idOrigen', 'uMedida', 'precio']
    campos_faltantes = [campo for campo in campos_requeridos if campo not in data]

    if campos_faltantes:
        return jsonify({
            "error": f"Campos requeridos faltantes: {', '.join(campos_faltantes)}"
        }), 400

    try:
        # Validar tipos de datos
        if not isinstance(data['precio'], (int, float)) or data['precio'] < 0:
            return jsonify({"error": "Precio debe ser un número positivo"}), 400

        with get_db() as db:
            # Verificar que el mercado exista
            mercado = db.query(Mercado).filter(
                Mercado.id == data['idOrigen']
            ).first()

            if not mercado:
                return jsonify({
                    "error": f"Mercado con ID {data['idOrigen']} no encontrado"
                }), 404

            # Crear nuevo producto
            nuevo_producto = Producto(
                nombre=data['nombre'],
                idOrigen=data['idOrigen'],
                uMedida=data['uMedida'],
                precio=int(data['precio'])
            )

            db.add(nuevo_producto)
            db.commit()
            db.refresh(nuevo_producto)

            return jsonify({
                "status": "success",
                "message": "Producto creado exitosamente",
                "producto": nuevo_producto.to_dict()
            }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# PUT /api/productos/<id> - Editar un producto por ID
@rutas.route("/productos/<int:idprd>", methods=["PUT"])
@requiere_api_key
def actualizar_producto(idprd):
    """Actualizar un producto existente"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No se proporcionó datos JSON"}), 400

    campos_permitidos = ['nombre', 'idOrigen', 'uMedida', 'precio']
    campos_actualizar = {k: v for k, v in data.items() if k in campos_permitidos}

    if not campos_actualizar:
        return jsonify({"error": "No hay campos válidos para actualizar"}), 400

    try:
        with get_db() as db:
            # Buscar producto
            producto = db.query(Producto).filter(Producto.id == idprd).first()

            if not producto:
                return jsonify({
                    "error": f"Producto con ID {idprd} no encontrado"
                }), 404

            # Si se actualiza idOrigen, verificar que el mercado exista
            if 'idOrigen' in campos_actualizar:
                mercado = db.query(Mercado).filter(
                    Mercado.id == campos_actualizar['idOrigen']
                ).first()

                if not mercado:
                    return jsonify({
                        "error": f"Mercado con ID {campos_actualizar['idOrigen']} no encontrado"
                    }), 404

            # Actualizar campos
            for campo, valor in campos_actualizar.items():
                if campo == 'precio':
                    if not isinstance(valor, (int, float)) or valor < 0:
                        return jsonify({"error": "Precio debe ser un número positivo"}), 400
                    valor = int(valor)
                setattr(producto, campo, valor)

            db.commit()
            db.refresh(producto)

            return jsonify({
                "status": "success",
                "message": "Producto actualizado exitosamente",
                "producto": producto.to_dict()
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# DELETE /api/productos/<id> - Eliminar un producto por ID
@rutas.route("/productos/<int:idprd>", methods=["DELETE"])
@requiere_api_key
def eliminar_producto(idprd):
    """Eliminar un producto"""
    try:
        with get_db() as db:
            producto = db.query(Producto).filter(Producto.id == idprd).first()

            if not producto:
                return jsonify({
                    "error": f"Producto con ID {idprd} no encontrado"
                }), 404

            producto_info = producto.to_dict()
            db.delete(producto)
            db.commit()

            return jsonify({
                "status": "success",
                "message": "Producto eliminado exitosamente",
                "producto_eliminado": producto_info
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Endpoint adicional para listar mercados
@rutas.route("/mercados", methods=["GET"])
@requiere_api_key
def listar_mercados():
    """Listar todos los mercados disponibles"""
    try:
        with get_db() as db:
            mercados = db.query(Mercado).all()
            return jsonify({
                "status": "success",
                "count": len(mercados),
                "mercados": [{"id": m.id, "nombre": m.nombre} for m in mercados]
            }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
