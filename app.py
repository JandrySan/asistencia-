from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime

app = Flask(__name__)
app.secret_key = 'clave_secreta'

# Conexión MongoDB Atlas (ajusta tus datos)
client = MongoClient("mongodb+srv://jandrypaulsanchez:HsJPpMVr8yBuwPcm@cluster0.hxlrvov.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['asistencia_db']
participantes_col = db['participantes']
asistencias_col = db['asistencias']

@app.route('/')
def home():
    return redirect(url_for('registrar_participante'))

@app.route('/participantes/nuevo', methods=['GET', 'POST'])
def registrar_participante():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        if nombre:
            participantes_col.insert_one({"nombre": nombre, "activo": True})
            flash('Participante registrado.', 'success')
            return redirect(url_for('listar_participantes'))
        else:
            flash('El nombre no puede estar vacío.', 'danger')
    return render_template('registrar_participante.html')

@app.route('/participantes')
def listar_participantes():
    participantes = list(participantes_col.find())
    return render_template('listar_participantes.html', participantes=participantes)

@app.route('/participantes/editar/<pid>', methods=['GET', 'POST'])
def editar_participante(pid):
    participante = participantes_col.find_one({"_id": ObjectId(pid)})
    if not participante:
        flash("Participante no encontrado", "danger")
        return redirect(url_for('listar_participantes'))

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        activo = request.form.get('activo') == 'on'
        if nombre:
            participantes_col.update_one({"_id": ObjectId(pid)}, {"$set": {"nombre": nombre, "activo": activo}})
            flash("Participante actualizado.", "success")
            return redirect(url_for('listar_participantes'))
        else:
            flash("El nombre no puede estar vacío.", "danger")

    return render_template('editar_participante.html', participante=participante)

@app.route('/participantes/eliminar/<pid>', methods=['POST'])
def eliminar_participante(pid):
    participante = participantes_col.find_one({"_id": ObjectId(pid)})
    if participante:
        participantes_col.delete_one({"_id": ObjectId(pid)})
        asistencias_col.delete_many({"participante_id": ObjectId(pid)})
        flash("Participante eliminado.", "success")
    else:
        flash("Participante no encontrado.", "danger")
    return redirect(url_for('listar_participantes'))

@app.route('/asistencia', methods=['GET', 'POST'])
def registrar_asistencia():
    participantes = list(participantes_col.find({"activo": True}))
    if request.method == 'POST':
        fecha = request.form['fecha']
        if not fecha:
            flash("Debe seleccionar una fecha.", "danger")
            return redirect(url_for('registrar_asistencia'))

        for p in participantes:
            pid = str(p['_id'])
            catequesis = request.form.get(f"catequesis_{pid}") == "on"
            misa = request.form.get(f"misa_{pid}") == "on"
            obs_catequesis = request.form.get(f"obs_catequesis_{pid}", "")
            obs_misa = request.form.get(f"obs_misa_{pid}", "")

            asistencias_col.update_one(
                {"participante_id": ObjectId(pid), "fecha": fecha},
                {"$set": {
                    "catequesis": catequesis,
                    "obs_catequesis": obs_catequesis,
                    "misa": misa,
                    "obs_misa": obs_misa
                }},
                upsert=True
            )
        flash(f"Asistencia registrada para {fecha}.", "success")
        return redirect(url_for('registrar_asistencia'))

    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d")
    return render_template('registrar_asistencia.html', participantes=participantes, fecha=fecha_actual)

@app.route('/asistencia/historial')
def historial_asistencia():
    fechas = asistencias_col.distinct("fecha")
    fechas.sort(reverse=True)
    return render_template('historial_asistencia.html', fechas=fechas)

@app.route('/asistencia/editar/<fecha>', methods=['GET', 'POST'])
def editar_asistencia(fecha):
    participantes = list(participantes_col.find({"activo": True}))
    registros = {str(a['participante_id']): a for a in asistencias_col.find({"fecha": fecha})}

    if request.method == 'POST':
        for p in participantes:
            pid = str(p['_id'])
            catequesis = request.form.get(f"catequesis_{pid}") == "on"
            misa = request.form.get(f"misa_{pid}") == "on"
            obs_catequesis = request.form.get(f"obs_catequesis_{pid}", "")
            obs_misa = request.form.get(f"obs_misa_{pid}", "")

            asistencias_col.update_one(
                {"participante_id": ObjectId(pid), "fecha": fecha},
                {"$set": {
                    "catequesis": catequesis,
                    "obs_catequesis": obs_catequesis,
                    "misa": misa,
                    "obs_misa": obs_misa
                }},
                upsert=True
            )
        flash(f"Asistencia actualizada para {fecha}.", "success")
        return redirect(url_for('historial_asistencia'))

    return render_template('editar_asistencia.html', fecha=fecha, participantes=participantes, registros=registros)

@app.route('/porcentaje')
def porcentaje():
    participantes = list(participantes_col.find({"activo": True}))
    total_fechas = len(asistencias_col.distinct("fecha"))
    resultados = []

    for p in participantes:
        catequesis_asistencias = asistencias_col.count_documents({"participante_id": p["_id"], "catequesis": True})
        misa_asistencias = asistencias_col.count_documents({"participante_id": p["_id"], "misa": True})
        porcentaje_catequesis = (catequesis_asistencias / total_fechas * 100) if total_fechas > 0 else 0
        porcentaje_misa = (misa_asistencias / total_fechas * 100) if total_fechas > 0 else 0

        resultados.append({
            "nombre": p["nombre"],
            "catequesis": round(porcentaje_catequesis, 2),
            "misa": round(porcentaje_misa, 2)
        })

    return render_template("porcentaje.html", resultados=resultados, total_dias=total_fechas)

@app.route('/reporte')
def reporte():
    flash("Funcionalidad PDF no implementada aún.", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
