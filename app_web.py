from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import pandas as pd
import os
from datetime import datetime
import logging

app = Flask(__name__)

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuraciones
app.config.update({
    'UPLOAD_FOLDER': 'static/uploads',
    'EXCEL_FILE': 'registros_cirugias.xlsx',
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    'ALLOWED_EXTENSIONS': {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'xls', 'xlsx'}
})

DTYPES = {
    'Fecha': 'datetime64[ns]',
    'Paciente': 'object',
    'Documento': 'object',
    'Cirujano': 'object',
    'Clínica': 'object',
    'Procedimiento': 'object',
    'Valor': 'float64',
    'Casa_Medica': 'object',
    'Documentos': 'object'
}

@app.context_processor
def inject_utilities():
    def format_date(value, format='%d/%m/%Y'):
        if value is None:
            return ""
        if isinstance(value, str):
            value = pd.to_datetime(value)
        return value.strftime(format)
    return {'now': datetime.now(), 'format_date': format_date}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def init_dataframe():
    if os.path.exists(app.config['EXCEL_FILE']):
        try:
            df = pd.read_excel(app.config['EXCEL_FILE'], dtype=DTYPES).fillna({
                'Documentos': '',
                'Casa_Medica': ''
            })
            for col in DTYPES.keys():
                if col not in df.columns:
                    df[col] = pd.Series(dtype=DTYPES[col])
            return df
        except Exception as e:
            logger.error(f"Error al leer archivo Excel: {str(e)}")
            return pd.DataFrame(columns=DTYPES.keys()).astype(DTYPES)
    return pd.DataFrame(columns=DTYPES.keys()).astype(DTYPES)

# Inicializar DataFrame
df = init_dataframe()

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/get_options')
def get_options():
    try:
        options = {
            'clinicas': sorted(df['Clínica'].dropna().unique().tolist()),
            'cirujanos': sorted(df['Cirujano'].dropna().unique().tolist()),
            'procedimientos': sorted(df['Procedimiento'].dropna().unique().tolist())
        }
        return jsonify(options)
    except Exception as e:
        logger.error(f"Error al obtener opciones: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        global df
        
        documentos = []
        try:
            for archivo in request.files.getlist('documentos'):
                if archivo.filename != '':
                    if not allowed_file(archivo.filename):
                        return render_template('formulario.html', 
                                            error="Tipo de archivo no permitido")
                    
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    nombre_archivo = secure_filename(f"{timestamp}_{archivo.filename}")
                    ruta_guardado = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
                    archivo.save(ruta_guardado)
                    documentos.append(nombre_archivo)
            
            required_fields = {
                'fecha': 'Fecha',
                'paciente': 'Paciente',
                'documento': 'Documento',
                'cirujano': 'Cirujano',
                'clinica': 'Clínica',
                'procedimiento': 'Procedimiento',
                'valor': 'Valor',
                'casa_medica': 'Casa_Medica'
            }
            
            form_data = {}
            for field, col_name in required_fields.items():
                value = request.form.get(field)
                if not value:
                    return render_template('formulario.html', 
                                        error=f"El campo {col_name} es requerido")
                form_data[col_name] = value.strip()
            
            nuevo_registro = {
                'Fecha': pd.to_datetime(form_data['Fecha']),
                'Paciente': form_data['Paciente'],
                'Documento': form_data['Documento'],
                'Cirujano': form_data['Cirujano'],
                'Clínica': form_data['Clínica'],
                'Procedimiento': form_data['Procedimiento'],
                'Valor': float(form_data['Valor']),
                'Casa_Medica': form_data['Casa_Medica'],
                'Documentos': ', '.join(documentos) if documentos else ''
            }
            
            df = pd.concat([df, pd.DataFrame([nuevo_registro])], ignore_index=True)
            df.to_excel(app.config['EXCEL_FILE'], index=False)
            return redirect(url_for('dashboard'))
                
        except ValueError as e:
            logger.error(f"Error de valor en registro: {str(e)}")
            return render_template('formulario.html', 
                                error="Error en los datos proporcionados")
        except Exception as e:
            logger.error(f"Error en registro: {str(e)}", exc_info=True)
            return render_template('formulario.html', 
                                error="Ocurrió un error al procesar el formulario")
    
    return render_template('formulario.html')

@app.route('/reporte', methods=['GET', 'POST'])
def reporte():
    fecha_inicio = request.form.get('fecha_inicio') if request.method == 'POST' else request.args.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin') if request.method == 'POST' else request.args.get('fecha_fin')
    
    mensaje = None
    total = 0
    por_cirujano = {}
    por_clinica = {}
    
    try:
        df_filtrado = df.copy()
        df_filtrado['Fecha'] = pd.to_datetime(df_filtrado['Fecha'])
        
        if fecha_inicio and fecha_fin:
            fecha_inicio_dt = pd.to_datetime(fecha_inicio)
            fecha_fin_dt = pd.to_datetime(fecha_fin)
            mask = (df_filtrado['Fecha'] >= fecha_inicio_dt) & (df_filtrado['Fecha'] <= fecha_fin_dt)
            df_filtrado = df_filtrado.loc[mask]
            
            if df_filtrado.empty:
                mensaje = "No hay registros en el rango de fechas seleccionado"
        
        df_filtrado = df_filtrado.sort_values('Fecha', ascending=False)
        
        total = float(df_filtrado['Valor'].sum())
        por_cirujano = df_filtrado.groupby('Cirujano')['Valor'].sum().sort_values(ascending=False).to_dict()
        por_clinica = df_filtrado.groupby('Clínica')['Valor'].sum().sort_values(ascending=False).to_dict()
        
        registros = []
        for idx, row in df_filtrado.iterrows():
            registro = {
                'id': idx,
                'fecha': row['Fecha'].strftime('%Y-%m-%d'),
                'paciente': row['Paciente'],
                'documento': row['Documento'],
                'cirujano': row['Cirujano'],
                'clinica': row['Clínica'],
                'procedimiento': row['Procedimiento'],
                'valor': float(row['Valor']),
                'valor_formateado': "${:,.2f}".format(float(row['Valor'])),
                'casa_medica': row['Casa_Medica'],
                'documentos': row['Documentos'].split(', ') if pd.notna(row['Documentos']) and row['Documentos'] != '' else []
            }
            registros.append(registro)
        
    except ValueError as e:
        mensaje = f"Error en formato de fecha: {str(e)}"
        registros = []
    except Exception as e:
        mensaje = f"Error inesperado: {str(e)}"
        logger.error(f"Error en reporte: {str(e)}", exc_info=True)
        registros = []
    
    return render_template('reporte.html',
                         total=total,
                         por_cirujano=por_cirujano,
                         por_clinica=por_clinica,
                         fecha_inicio=fecha_inicio,
                         fecha_fin=fecha_fin,
                         mensaje=mensaje,
                         registros=registros)

@app.route('/descargar_excel')
def descargar_excel():
    try:
        return send_from_directory('.', app.config['EXCEL_FILE'], 
                                 as_attachment=True,
                                 download_name='registros_cirugias.xlsx')
    except Exception as e:
        logger.error(f"Error al descargar Excel: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/descargar/<filename>')
def descargar_archivo(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_registro(id):
    global df
    
    try:
        registro = df.iloc[id].to_dict()
        registro['Fecha'] = registro['Fecha'].strftime('%Y-%m-%d')
    except IndexError:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            documentos = []
            for file in request.files.getlist('documentos'):
                if file.filename != '' and allowed_file(file.filename):
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    filename = secure_filename(f"{timestamp}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    documentos.append(filename)
            
            required_fields = {
                'fecha': 'Fecha',
                'paciente': 'Paciente',
                'documento': 'Documento',
                'cirujano': 'Cirujano',
                'clinica': 'Clínica',
                'procedimiento': 'Procedimiento',
                'valor': 'Valor',
                'casa_medica': 'Casa_Medica'
            }
            
            updates = {}
            for field, col_name in required_fields.items():
                value = request.form.get(field)
                if not value:
                    return render_template('editar.html', 
                                         registro=registro,
                                         error=f"El campo {col_name} es requerido")
                updates[col_name] = value.strip()
            
            updates['Fecha'] = pd.to_datetime(updates['Fecha'])
            updates['Valor'] = float(updates['Valor'])
            
            if documentos:
                docs_existentes = registro['Documentos'].split(', ') if registro['Documentos'] else []
                updates['Documentos'] = ', '.join(docs_existentes + documentos)
            
            for key, value in updates.items():
                df.at[id, key] = value
            
            df.to_excel(app.config['EXCEL_FILE'], index=False)
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            logger.error(f"Error de valor al editar registro: {str(e)}")
            return render_template('editar.html', 
                                 registro=registro,
                                 error="Error en los datos proporcionados")
        except Exception as e:
            logger.error(f"Error al editar registro: {str(e)}", exc_info=True)
            return render_template('editar.html', 
                                 registro=registro,
                                 error="Error al actualizar el registro")
    
    return render_template('editar.html', registro=registro)

@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar_registro(id):
    global df
    
    try:
        registro = df.iloc[id]
        if registro['Documentos']:
            for doc in registro['Documentos'].split(', '):
                doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc)
                if os.path.exists(doc_path):
                    try:
                        os.remove(doc_path)
                    except Exception as e:
                        logger.error(f"Error al eliminar archivo {doc}: {str(e)}")
        
        df = df.drop(id).reset_index(drop=True)
        df.to_excel(app.config['EXCEL_FILE'], index=False)
        return redirect(url_for('dashboard'))
    
    except Exception as e:
        logger.error(f"Error al eliminar registro: {str(e)}", exc_info=True)
        return redirect(url_for('dashboard'))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                             'favicon.ico', 
                             mimetype='image/vnd.microsoft.icon')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    try:
        fecha_inicio = request.form.get('fecha_inicio') if request.method == 'POST' else request.args.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin') if request.method == 'POST' else request.args.get('fecha_fin')
        
        df_dash = df.copy()
        df_dash['Fecha'] = pd.to_datetime(df_dash['Fecha'], errors='coerce')
        df_dash = df_dash.dropna(subset=['Fecha'])
        
        if fecha_inicio and fecha_fin:
            fecha_inicio_dt = pd.to_datetime(fecha_inicio)
            fecha_fin_dt = pd.to_datetime(fecha_fin)
            mask = (df_dash['Fecha'] >= fecha_inicio_dt) & (df_dash['Fecha'] <= fecha_fin_dt)
            df_dash = df_dash.loc[mask]
        
        df_dash['Mes'] = df_dash['Fecha'].dt.to_period('M').astype(str)
        
        mensual = df_dash.groupby('Mes', as_index=False)['Valor'].sum() \
                  .rename(columns={'Valor': 'Valor'})
        mensual['Valor'] = mensual['Valor'].astype(float)
        mensual = mensual.to_dict('records')
        
        top_cirujanos = df_dash.groupby('Cirujano', as_index=False)['Valor'].sum() \
                          .nlargest(5, 'Valor')
        top_cirujanos['Valor'] = top_cirujanos['Valor'].astype(float)
        top_cirujanos = top_cirujanos.to_dict('records')
        
        top_clinicas = df_dash.groupby('Clínica', as_index=False)['Valor'].sum() \
                         .nlargest(5, 'Valor')
        top_clinicas['Valor'] = top_clinicas['Valor'].astype(float)
        top_clinicas = top_clinicas.to_dict('records')
        
        por_casa_medica = df_dash.groupby('Casa_Medica', as_index=False)['Valor'] \
                         .sum() \
                         .sort_values('Valor', ascending=False) \
                         .head(10)
        por_casa_medica = por_casa_medica.to_dict('records')

        return render_template('dashboard.html',
                            mensual=mensual or [{'Mes': datetime.now().strftime('%Y-%m'), 'Valor': 0}],
                            top_cirujanos=top_cirujanos or [],
                            top_clinicas=top_clinicas or [],
                            por_casa_medica=por_casa_medica or [],
                            total_general=float(df_dash['Valor'].sum()) or 0,
                            cantidad_cirugias=len(df_dash),
                            fecha_inicio=fecha_inicio,
                            fecha_fin=fecha_fin)
    
    except Exception as e:
        logger.error(f"Error en dashboard: {str(e)}", exc_info=True)
        return render_template('error.html',
                            message="Error al generar el dashboard",
                            error=str(e)), 500

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    if os.environ.get('FLASK_ENV') == 'production':
        try:
            from waitress import serve
            serve(app, host='0.0.0.0', port=5000)
        except ImportError:
            logger.warning("Waitress no está instalado. Usando servidor de desarrollo Flask.")
            app.run(host='0.0.0.0', port=5000)
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)