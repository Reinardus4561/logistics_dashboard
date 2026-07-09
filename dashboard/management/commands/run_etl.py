import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.models import (
    OpCity, OpCustomer, OpDriver, OpVehicle, OpShipment
)
from dashboard.services import ETLPipeline

class Command(BaseCommand):
    help = "Menjalankan proses ETL dari OLTP (Operasional) ke OLAP (Data Warehouse)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--seed',
            action='store_true',
            help='Isi tabel operasional dengan data simulasi kotor sebelum menjalankan ETL.',
        )

    def handle(self, *args, **options):
        if options['seed']:
            self.stdout.write("Memulai seeding data kotor ke basis data operasional...")
            self.seed_operational_data()
            self.stdout.write(self.style.SUCCESS("Seeding data operasional berhasil."))

        self.stdout.write("Memulai pemrosesan ETL...")
        pipeline = ETLPipeline()
        success, result = pipeline.run()

        if success:
            self.stdout.write(self.style.SUCCESS("Proses ETL Selesai dengan sukses!"))
            self.stdout.write(f"  - Data diekstraksi: {result['extracted']}")
            self.stdout.write(f"  - Duplikat dibuang: {result['duplicates_removed']}")
            self.stdout.write(f"  - Data NULL ditangani: {result['nulls_handled']}")
            self.stdout.write(f"  - Standarisasi format: {result['standardized']}")
            self.stdout.write(f"  - Data dimuat ke DWH: {result['loaded']}")
        else:
            self.stdout.write(self.style.ERROR(f"Proses ETL gagal: {result}"))

    def seed_operational_data(self):
        # 1. Hapus data lama di operasional
        OpShipment.objects.all().delete()
        OpCustomer.objects.all().delete()
        OpDriver.objects.all().delete()
        OpVehicle.objects.all().delete()
        OpCity.objects.all().delete()

        # 2. Buat Kota (dengan beberapa nama kotor/singkatan)
        cities_data = ["Jakarta", "sby", "bdg", "Medan", "mks"]
        cities = []
        for c in cities_data:
            cities.append(OpCity.objects.create(city_name=c))

        # 3. Buat Pelanggan
        customers = []
        cust_names = ["PT ABC Logistics", "PT Indofood", "CV Maju Jaya", "PT Tokopedia", "PT Shopee Express", None]
        for i, name in enumerate(cust_names):
            cust_id = f"CUST{i+1:03d}"
            # Hubungkan ke kota secara acak, ada yang NULL
            city_obj = random.choice(cities) if name else None
            customers.append(
                OpCustomer.objects.create(
                    customer_id=cust_id,
                    customer_name=name,
                    city=city_obj
                )
            )

        # 4. Buat Drivers
        drivers = []
        driver_names = [
            ("D001", "Joko", "08123456789", "A-12345"),
            ("D002", "Agus", "08234567890", "B-67890"),
            ("D003", "Rudi", "08345678901", "C-11121"),
            ("D004", "Budi", None, "D-13141"),
            ("D005", "Unknown Driver", "08456789012", None)
        ]
        for did, name, phone, lic in driver_names:
            drivers.append(
                OpDriver.objects.create(
                    driver_id=did,
                    driver_name=name,
                    phone=phone,
                    license_number=lic,
                    status="Active" if name != "Budi" else "Suspended"
                )
            )

        # 5. Buat Kendaraan
        vehicles = []
        veh_data = [
            ("V001", "Truck", "B 9999 AA", 8.0, 500000),
            ("V002", "Van", "D 8888 BB", 12.0, 200000),
            ("V003", "Container", "L 7777 CC", 5.0, 1000000),
            ("V004", "Truck", "BK 6666 DD", 8.5, 450000),
            ("V005", "Pick Up", None, 10.0, 150000)
        ]
        for vid, vtype, plate, fuel, maint in veh_data:
            vehicles.append(
                OpVehicle.objects.create(
                    vehicle_id=vid,
                    vehicle_type=vtype,
                    license_plate=plate,
                    fuel_consumption=fuel,
                    maintenance_cost=maint,
                    status="Active"
                )
            )

        # 6. Buat Pengiriman (Shipment)
        now = timezone.now()
        statuses = ["dlv", "trn", "can", "Delivered", "In Transit", "Cancelled"]

        # Kita buat 100 baris data pengiriman
        # Beberapa baris sengaja diduplikat secara logika untuk menguji data cleaning
        shipments_to_create = []
        for i in range(120):
            # Acak data
            cust = random.choice(customers)
            driver = random.choice(drivers)
            vehicle = random.choice(vehicles)
            city = random.choice(cities)
            
            # Waktu pengiriman dalam 30 hari ke belakang, dan ada 1 yang di masa depan
            days_ago = random.randint(-2, 30) # negatif berarti masa depan
            ship_date = now - timedelta(days=days_ago)

            distance = round(random.uniform(10.0, 600.0), 2)
            delay = round(random.uniform(0.0, 120.0), 1)

            # Ada yang null untuk diuji transformasinya
            cost = None if random.random() < 0.15 else int(distance * 4800 + 50000)
            time_hours = None if random.random() < 0.15 else max(1, int(distance / 45.0))
            
            status = random.choice(statuses)

            shipments_to_create.append({
                'customer': cust,
                'driver': driver,
                'vehicle': vehicle,
                'city': city,
                'shipment_date': ship_date,
                'delivery_cost': cost,
                'delivery_time_hours': time_hours,
                'distance_km': distance,
                'delay_minutes': delay,
                'status': status
            })

        # Sisipkan duplikasi sengaja (misal 15 baris)
        duplicates = random.sample(shipments_to_create, 15)
        shipments_to_create.extend(duplicates)

        # Simpan ke basis data
        for s in shipments_to_create:
            OpShipment.objects.create(**s)
