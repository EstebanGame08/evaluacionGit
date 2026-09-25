# -*- coding: utf-8 -*-
# ============================================================
#  Algoritmo de validacion de una solicitud de autorizacion
#  Sistema de informacion de una EPS - microservicio ms-autorizaciones
#
#  Ingenieria de Software III (FI303290) - UNIAJC
#  Esteban Antonio Estrada Angulo - GitHub: EstebanGame08
# ============================================================
#
#  Reproduce, en un solo archivo y sin dependencias, la cadena
#  de validaciones que el diagrama de secuencia del documento
#  Docs/Arquitectura_EPS.docx describe repartida entre varios
#  microservicios.
#
#  El orden de las validaciones no es arbitrario: van de la mas
#  barata y mas probable de fallar hacia la mas costosa, para
#  cortar el flujo lo antes posible.
# ============================================================


# ------------------------------------------------------------
#  Datos simulados (en el sistema real cada bloque vendria de
#  la API de su microservicio, no de un diccionario local)
# ------------------------------------------------------------

AFILIADOS = {
    "1144098876": {"nombre": "Carlos Lopez",   "estado": "ACTIVO",   "regimen": "CONTRIBUTIVO"},
    "1006554321": {"nombre": "Maria Torres",   "estado": "ACTIVO",   "regimen": "SUBSIDIADO"},
    "94231007":   {"nombre": "Luis Herrera",   "estado": "RETIRADO", "regimen": "CONTRIBUTIVO"},
    "1193887654": {"nombre": "Ana Quintero",   "estado": "SUSPENDIDO", "regimen": "CONTRIBUTIVO"},
}

# Red de prestadores: que codigos CUPS tiene habilitados cada IPS
PRESTADORES = {
    "890303461": {"nombre": "IPS Norte",     "cups": ["890201", "890301", "902210"]},
    "805027337": {"nombre": "IPS Occidente", "cups": ["890201", "881234"]},
}

# Procedimientos y si estan cubiertos por el plan de beneficios
PROCEDIMIENTOS = {
    "890201": {"nombre": "Consulta medicina general", "pbs": True},
    "890301": {"nombre": "Consulta especializada",    "pbs": True},
    "902210": {"nombre": "Hemograma completo",        "pbs": True},
    "881234": {"nombre": "Terapia alternativa",       "pbs": False},
}


# ------------------------------------------------------------
#  Validaciones individuales
#  Cada una devuelve (aprobada, motivo)
# ------------------------------------------------------------

def validar_afiliado(documento):
    """Equivale a la llamada GET /afiliados/{doc}/estado."""
    afiliado = AFILIADOS.get(documento)

    if afiliado is None:
        return False, "El documento " + documento + " no figura como afiliado"

    if afiliado["estado"] == "RETIRADO":
        return False, afiliado["nombre"] + " esta retirado y no tiene derechos activos"

    if afiliado["estado"] == "SUSPENDIDO":
        return False, afiliado["nombre"] + " tiene la afiliacion suspendida por mora"

    return True, afiliado["nombre"] + " esta activo en regimen " + afiliado["regimen"]


def validar_procedimiento(cups):
    """Verifica que el codigo exista y este cubierto por el plan."""
    procedimiento = PROCEDIMIENTOS.get(cups)

    if procedimiento is None:
        return False, "El codigo CUPS " + cups + " no existe en el maestro"

    if not procedimiento["pbs"]:
        return False, (procedimiento["nombre"]
                       + " es no PBS: requiere tramite por MIPRES")

    return True, procedimiento["nombre"] + " esta cubierto por el plan"


def validar_prestador(nit, cups):
    """Equivale a GET /prestadores/{nit}/contrato?cups={codigo}."""
    prestador = PRESTADORES.get(nit)

    if prestador is None:
        return False, "La IPS con NIT " + nit + " no pertenece a la red contratada"

    if cups not in prestador["cups"]:
        return False, (prestador["nombre"]
                       + " no tiene habilitado el procedimiento " + cups)

    return True, prestador["nombre"] + " tiene el procedimiento habilitado"


# ------------------------------------------------------------
#  Orquestacion: la cadena completa
# ------------------------------------------------------------

def procesar_solicitud(consecutivo, documento, nit_ips, cups):
    """
    Ejecuta las tres validaciones en orden y corta en la primera
    que falle. Devuelve el numero de autorizacion o None.
    """
    print("-" * 58)
    print("Solicitud " + consecutivo
          + " | doc " + documento
          + " | IPS " + nit_ips
          + " | CUPS " + cups)

    validaciones = [
        ("Afiliacion",    validar_afiliado(documento)),
        ("Procedimiento", validar_procedimiento(cups)),
        ("Prestador",     validar_prestador(nit_ips, cups)),
    ]

    for etapa, (aprobada, motivo) in validaciones:
        if not aprobada:
            print("  [RECHAZADA] " + etapa + ": " + motivo)
            return None
        print("  [OK] " + etapa + ": " + motivo)

    numero = "AUT-" + consecutivo
    print("  [APROBADA] Numero de autorizacion: " + numero)
    print("  -> se publica el evento autorizacion.emitida en el bus")
    return numero


# ------------------------------------------------------------
#  Corrida de prueba
# ------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 58)
    print("  VALIDACION DE SOLICITUDES DE AUTORIZACION")
    print("=" * 58)

    casos = [
        # consecutivo, documento, NIT de la IPS, codigo CUPS
        ("2026-0001", "1144098876", "890303461", "890301"),  # aprobada
        ("2026-0002", "94231007",   "890303461", "890201"),  # afiliado retirado
        ("2026-0003", "1193887654", "890303461", "890201"),  # suspendido por mora
        ("2026-0004", "1006554321", "805027337", "881234"),  # procedimiento no PBS
        ("2026-0005", "1144098876", "805027337", "902210"),  # IPS sin habilitacion
        ("2026-0006", "1006554321", "890303461", "902210"),  # aprobada
    ]

    emitidas = 0
    for consecutivo, documento, nit, cups in casos:
        if procesar_solicitud(consecutivo, documento, nit, cups) is not None:
            emitidas += 1

    print("-" * 58)
    print("Procesadas: " + str(len(casos))
          + "  |  Aprobadas: " + str(emitidas)
          + "  |  Rechazadas: " + str(len(casos) - emitidas))
