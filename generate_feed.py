import json
import psycopg2
from datetime import datetime
from psycopg2.extras import RealDictCursor

OUTPUT_FILE = "feed.json"
def waze():
    # conn = psycopg2.connect('postgresql://analytics:An4lytik009@192.168.3.89:5432/analytics')
    conn = psycopg2.connect('postgresql://jaki_data:V6nPcxt85y6tnyDa2hfXNOnmf@192.168.3.43:5432/jakiv2_peta')
    query = r"""
    with data_bersih as (
                            select a.id, a."name" as nama, b."name" as nama_kategori, a.maps_id, a.address,  
                            a."location", a.created_at,
                            split_part(replace(replace(a."location", 'POINT(', ''), ')', ''), ' ', 1)::numeric AS lng,
                            split_part(replace(replace(a."location", 'POINT(', ''), ')', ''), ' ', 2)::numeric AS lat,
                            a.description, 
                            TRIM(substring(a.description FROM '<b>1\. Jenis Pekerjaan:</b>(.*?)<br>')) AS jenis_pekerjaan,
                                TRIM(substring(a.description FROM '<b>2\. Lokasi:</b>(.*?)<br>')) AS lokasi,
                                TRIM(substring(a.description FROM '<b>4\. Potensi dampak:</b>(.*?)<br>')) AS potensi_dampak,
                                REPLACE(TRIM(substring(a.description FROM '<b>5\. Penanggung Jawab:</b>(.*)')), '<br>', ' ') AS penanggung_jawab,
                            a.phone_number, a.array_image_url,
                                TRIM(substring(a.description FROM '<b>3\. Jadwal Pekerjaan:</b>(.*?)<br>')) AS jadwal_pekerjaan
                            from markers a left join maps b on a.maps_id = b.id
                            where b."name" ilike '%konstruksi%'), 
            data_bersih2 as (
                            select *, 
                            case 
                                when jadwal_pekerjaan ilike '%tbu%' then null
                            else jadwal_pekerjaan
                                end as jadwal_pekerjaans
                            from data_bersih ),	
            data_bersih3 as (
                            select *, 
                                TRIM(SPLIT_PART(jadwal_pekerjaans, ' s/d ', 1)) AS start_date,
                                TRIM(SPLIT_PART(jadwal_pekerjaans, ' s/d ', 2)) AS end_date
                            from data_bersih2)
            ,data_bersih4 AS (
                            SELECT *,
                                -- 1. Ubah spasi dan garis miring menjadi strip (-), lalu terjemahkan teks bulan ke angka
                                REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                                REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                                    REGEXP_REPLACE(LOWER(start_date), '[\s/]+', '-', 'g'),
                                '-januari-', '-01-'), '-februari-', '-02-'), '-maret-', '-03-'),
                                '-april-', '-04-'), '-mei-', '-05-'), '-juni-', '-06-'),
                                '-juli-', '-07-'), '-agustus-', '-08-'), '-september-', '-09-'),
                                '-oktober-', '-10-'), '-november-', '-11-'), '-desember-', '-12-') AS start_date2, 
                                REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                                REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                                    REGEXP_REPLACE(LOWER(end_date), '[\s/]+', '-', 'g'),
                                '-januari-', '-01-'), '-februari-', '-02-'), '-maret-', '-03-'),
                                '-april-', '-04-'), '-mei-', '-05-'), '-juni-', '-06-'),
                                '-juli-', '-07-'), '-agustus-', '-08-'), '-september-', '-09-'),
                                '-oktober-', '-10-'), '-november-', '-11-'), '-desember-', '-12-') AS end_date2 
                            FROM data_bersih3)
            , data_bersih5 as (
                                SELECT *,
                                CASE 
                                        WHEN start_date ~* '^\d{1,2}[\s/-]+[a-z0-9]+[\s/-]+\d{2,4}$' THEN
                                            LPAD(SPLIT_PART(start_date2, '-', 1), 2, '0') || '-' ||
                                            LPAD(SPLIT_PART(start_date2, '-', 2), 2, '0') || '-' ||
                                            CASE 
                                                WHEN LENGTH(SPLIT_PART(start_date2, '-', 3)) = 2 THEN '20' || SPLIT_PART(start_date2, '-', 3)
                                                ELSE SPLIT_PART(start_date2, '-', 3)
                                            end 
                                        ELSE 
                                            start_date
                                    END AS start_date3,
                                    CASE 
                                        WHEN end_date ~* '^\d{1,2}[\s/-]+[a-z0-9]+[\s/-]+\d{2,4}$' THEN
                                            LPAD(SPLIT_PART(end_date2, '-', 1), 2, '0') || '-' ||
                                            LPAD(SPLIT_PART(end_date2, '-', 2), 2, '0') || '-' ||
                                            CASE 
                                                WHEN LENGTH(SPLIT_PART(end_date2, '-', 3)) = 2 THEN '20' || SPLIT_PART(end_date2, '-', 3)
                                                ELSE SPLIT_PART(end_date2, '-', 3)
                                            end 
                                        ELSE 
                                            end_date
                                    END AS end_date3,
                                TRIM(
                    -- 3. Hapus sisa tag HTML seperti <b> dan </b>
                    REGEXP_REPLACE(
                        -- 2. Ubah <br> dan spasi di sekitarnya menjadi baris baru (Enter)
                        REGEXP_REPLACE(
                            -- 1. Buang semua teks berulang setelah tanda pipa (|)
                            SPLIT_PART(description, '|', 1), 
                        '\s*<br>\s*', E'\n', 'gi'), 
                    '<[^>]+>', '', 'g')
                ) AS deskripsi
                                    FROM data_bersih4)
            select 
--			count(*)
            id, nama as nama_lokasi, maps_id, "location" as lokasi ,lng, lat,  address, phone_number, array_image_url, deskripsi, jenis_pekerjaan, lokasi, potensi_dampak, 
            penanggung_jawab, phone_number, start_date3 as start_date, end_date3 as end_date, created_at
--            , TO_DATE(end_date3, 'DD-MM-YYYY') as end_date_to
            from data_bersih5
 			where 
 			(end_date3 !~ '[A-Za-z]')
 			and
 			TO_DATE(end_date3, 'DD-MM-YYYY') >= NOW()::date ;
            """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

def clean_text(value):
    """Membersihkan string."""
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
        row["lng"],
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
        clean_text(row["lokasi"])
        or clean_text(row["nama_lokasi"])
        or clean_text(row["address"])
    )

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------
    description = row["deskripsi"]

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------
    starttime = parse_datetime(row["start_date"])
    endtime = parse_datetime(row["end_date"])

    # --------------------------------------------------------
    # INCIDENT
    # --------------------------------------------------------
    incident = {
        "id": event_id,
        "type": "HAZARD",
        "subtype": "HAZARD_ON_ROAD_CONSTRUCTION",
        "direction": "BOTH_DIRECTIONS",
        "description": description,
        "street": street,
        "polyline": (
            # f"{longitude:.7f}"
            f"{latitude:.7f} "
            f"{longitude:.7f}"
        )
    }
    # --------------------------------------------------------
    # OPTIONAL DATE
    # --------------------------------------------------------
    if starttime:
        incident["start_date"] = starttime
    if endtime:
        incident["end_date"] = endtime
    return incident

def main():
    try:
        rows = waze()
        # print(type(rows), rows)
        print(f"Data ditemukan: {len(rows)}")

        incidents = []
        used_ids = set()
        success = 0
        failed = 0

        for row in rows:
            print(row)
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
                incident = create_incident(row)
                incidents.append(incident)
                success += 1

            except Exception as error:
                failed += 1
                print(f"[ERROR] " f"{event_id}: {error}")
        feed = {
            "incidents": incidents
        }
        with open(OUTPUT_FILE,"w",encoding="utf-8") as file:
            json.dump(
                feed,
                file,
                ensure_ascii=False,
                indent=2)

        print("Feed berhasil dibuat")
        print(f"File    : {OUTPUT_FILE}")
        print(f"Success : {success}")
        print(f"Failed  : {failed}")
    except Exception as error:
        print(error)
        raise
if __name__ == "__main__":
    main()