import json
import psycopg2
from datetime import datetime
from psycopg2.extras import RealDictCursor

TABLE_NAME = "waze_events"
OUTPUT_FILE = "feed_ujicoba.json"

SQL = f"""
SELECT
    id2 as id,
    name,
    maps_id,
    location,
    address,
    description,
    phone_number,
    array_image_url,
    jenis_pekerjaan,
    lokasi_pekerjaan,
    jadwal_pekerjaan,
    potensi_dampak,
    penanggung_jawab,
    -- id2,
    long,
    lat,
    tanggal_mulai,
    tanggal_selesai
FROM {TABLE_NAME}
WHERE lat IS NOT NULL
  AND long IS NOT NULL
"""

def clean_text(value):
    """
    Membersihkan string.
    """
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


# ============================================================
# PARSE COORDINATE
# ============================================================
def parse_coordinate(value, coordinate_type):
    """
    Mengubah varchar latitude/longitude menjadi float.
    """
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    # Hilangkan kemungkinan spasi
    value = value.replace(" ", "")
    try:
        number = float(value)
    except ValueError:
        raise ValueError(
            f"{coordinate_type} tidak valid: {value}"
        )

    # Validasi latitude
    if coordinate_type == "latitude":

        if not -90 <= number <= 90:

            raise ValueError(
                f"Latitude di luar range: {number}"
            )

    # Validasi longitude
    elif coordinate_type == "longitude":

        if not -180 <= number <= 180:

            raise ValueError(
                f"Longitude di luar range: {number}"
            )

    return number


# ============================================================
# PARSE DATETIME
# ============================================================
def parse_datetime(value):
    """
    Mencoba membaca berbagai format tanggal
    dari database.
    """
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(
                value,
                fmt
            )
            return dt.strftime(
                "%Y-%m-%dT%H:%M:%S+07:00"
            )

        except ValueError:

            continue

    raise ValueError(
        f"Format tanggal tidak dikenali: {value}"
    )


# ============================================================
# GENERATE DESCRIPTION
# ============================================================
def generate_description(row):
    """
    Menggabungkan informasi yang relevan
    menjadi description.
    """
    parts = []
    description = clean_text(
        row["description"]
    )
    jenis_pekerjaan = clean_text(
        row["jenis_pekerjaan"]
    )
    potensi_dampak = clean_text(
        row["potensi_dampak"]
    )
    penanggung_jawab = clean_text(
        row["penanggung_jawab"]
    )
    jadwal_pekerjaan = clean_text(
        row["jadwal_pekerjaan"]
    )
    if description:
        parts.append(description)

    if jenis_pekerjaan:
        parts.append(
            f"Jenis pekerjaan: {jenis_pekerjaan}"
        )

    if potensi_dampak:
        parts.append(
            f"Potensi dampak: {potensi_dampak}"
        )

    if jadwal_pekerjaan:
        parts.append(
            f"Jadwal: {jadwal_pekerjaan}"
        )

    if penanggung_jawab:
        parts.append(
            f"Penanggung jawab: {penanggung_jawab}"
        )

    return " | ".join(parts)


# ============================================================
# CREATE INCIDENT
# ============================================================

def create_incident(row):

    event_id = clean_text(
        row["id"]
    )

    if not event_id:

        raise ValueError(
            "ID kosong"
        )

    latitude = parse_coordinate(
        row["lat"],
        "latitude"
    )

    longitude = parse_coordinate(
        row["long"],
        "longitude"
    )

    if latitude is None:

        raise ValueError(
            f"Latitude kosong untuk ID {event_id}"
        )

    if longitude is None:

        raise ValueError(
            f"Longitude kosong untuk ID {event_id}"
        )

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    street = (
        clean_text(row["lokasi_pekerjaan"])
        or clean_text(row["location"])
        or clean_text(row["name"])
        or clean_text(row["address"])
    )

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    description = generate_description(
        row
    )

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    starttime = parse_datetime(
        row["tanggal_mulai"]
    )

    endtime = parse_datetime(
        row["tanggal_selesai"]
    )

    # --------------------------------------------------------
    # INCIDENT
    # --------------------------------------------------------

    incident = {
        "id": event_id,

        "type": "HAZARD",

        "subtype": "HAZARD_ON_ROAD_CONSTRUCTION",

        "description": description,

        "street": street,

        "polyline": (
            f"{latitude:.7f} "
            f"{longitude:.7f}"
        )
    }

    # --------------------------------------------------------
    # OPTIONAL DATE
    # --------------------------------------------------------

    if starttime:
        incident["starttime"] = starttime
    if endtime:
        incident["endtime"] = endtime
    return incident


# ============================================================
# GENERATE FEED
# ============================================================

def generate_feed():

    conn = None
    cursor = None

    try:
        print("Connecting PostgreSQL...")
        connection = psycopg2.connect('postgresql://postgres:data4jsc2021!@192.168.3.187:5432/data-dev')
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        print("Executing query...")
        cursor.execute(SQL)
        rows = cursor.fetchall()
        print(
            f"Data ditemukan: {len(rows)}"
        )

        incidents = []

        used_ids = set()

        success = 0
        failed = 0

        for row in rows:

            event_id = clean_text(
                row["id"]
            )

            try:

                # --------------------------------------------
                # CHECK DUPLICATE ID
                # --------------------------------------------

                if event_id in used_ids:

                    raise ValueError(
                        f"Duplicate ID: {event_id}"
                    )

                used_ids.add(
                    event_id
                )

                # --------------------------------------------
                # CREATE INCIDENT
                # --------------------------------------------

                incident = create_incident(
                    row
                )

                incidents.append(
                    incident
                )

                success += 1

            except Exception as error:

                failed += 1

                print(
                    f"[ERROR] "
                    f"{event_id}: {error}"
                )

        # ----------------------------------------------------
        # CREATE FEED
        # ----------------------------------------------------

        feed = {
            "incidents": incidents
        }

        # ----------------------------------------------------
        # WRITE JSON
        # ----------------------------------------------------

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                feed,
                file,
                ensure_ascii=False,
                indent=2
            )

        print()
        print(
            "======================================"
        )

        print(
            "Feed berhasil dibuat"
        )

        print(
            f"File    : {OUTPUT_FILE}"
        )

        print(
            f"Success : {success}"
        )

        print(
            f"Failed  : {failed}"
        )

        print(
            "======================================"
        )

    except Exception as error:

        print()
        print(
            "ERROR DATABASE / SYSTEM:"
        )

        print(
            error
        )
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    generate_feed()