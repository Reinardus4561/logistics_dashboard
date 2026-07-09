import logging
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.db.models import Max
from .models import (
    OpCity, OpCustomer, OpDriver, OpVehicle, OpShipment,
    DimCity, DimCustomer, DimDriver, DimTime, DimVehicle, FactDelivery
)

logger = logging.getLogger(__name__)

class ETLPipeline:
    def __init__(self):
        self.stats = {
            'extracted': 0,
            'duplicates_removed': 0,
            'nulls_handled': 0,
            'standardized': 0,
            'loaded': 0
        }

    def run(self):
        """
        Menjalankan seluruh pipa ETL (Extract, Clean, Transform, Load) secara transaksional.
        """
        logger.info("Memulai proses ETL...")
        try:
            with transaction.atomic():
                # 1. EXTRACT
                raw_shipments = self.extract()
                
                # 2. CLEAN & TRANSFORM
                cleaned_data = self.clean_and_transform(raw_shipments)
                
                # 3. LOAD
                self.load(cleaned_data)
                
            logger.info("Proses ETL selesai dengan sukses.")
            return True, self.stats
        except Exception as e:
            logger.error(f"Proses ETL gagal: {str(e)}", exc_info=True)
            return False, str(e)

    def extract(self):
        """
        Extract: Mengambil seluruh data mentah dari tabel operasional (OLTP).
        """
        shipments = list(OpShipment.objects.select_related('customer', 'driver', 'vehicle', 'city').all())
        self.stats['extracted'] = len(shipments)
        logger.info(f"Extract: Berhasil mengambil {len(shipments)} data pengiriman dari op_shipment.")
        return shipments

    def clean_and_transform(self, shipments):
        """
        Clean & Transform: Pembersihan data kotor dan pengayaan data (kalkulasi metrik).
        """
        seen_keys = set()
        cleaned_records = []

        # Default fallback values for dimensions
        # Menjamin ketersediaan dimensi default jika data operasional NULL
        default_city_name = "Jakarta"
        default_customer_info = {'id': 'C_UNK', 'name': 'Unknown Customer'}
        default_driver_info = {'id': 'D_UNK', 'name': 'Unknown Driver', 'phone': '-', 'license': '-', 'status': 'Active'}
        default_vehicle_info = {'id': 'V_UNK', 'type': 'Unknown Vehicle', 'plate': '-', 'fuel': 10.0, 'maintenance': 0.0, 'status': 'Active'}

        for ship in shipments:
            # --- 1. MENGHAPUS DUPLIKAT ---
            # Menggunakan composite key dari data transaksi untuk mendeteksi duplikat logika
            ship_date_str = str(ship.shipment_date.date()) if ship.shipment_date else 'null'
            composite_key = (
                ship.customer_id, 
                ship.driver_id, 
                ship.vehicle_id, 
                ship_date_str, 
                ship.distance_km, 
                ship.delivery_cost
            )
            if composite_key in seen_keys:
                self.stats['duplicates_removed'] += 1
                continue
            seen_keys.add(composite_key)

            # --- 2. PENANGANAN NULLS & STANDARISASI ---
            # Kota
            city_name = default_city_name
            if ship.city:
                city_name = ship.city.city_name
            elif ship.customer and ship.customer.city:
                city_name = ship.customer.city.city_name
            
            # Standarisasi Nama Kota
            city_lower = city_name.strip().lower()
            if city_lower in ['jkt', 'jakarta', 'dki jakarta', 'jkt-pusat', 'jkt-barat', 'jkt-utara', 'jkt-selatan', 'jkt-timur']:
                city_name = "Jakarta"
            elif city_lower in ['sby', 'surabaya', 'suroboyo']:
                city_name = "Surabaya"
            elif city_lower in ['bdg', 'bandung']:
                city_name = "Bandung"
            elif city_lower in ['mdn', 'medan']:
                city_name = "Medan"
            elif city_lower in ['mks', 'makassar']:
                city_name = "Makassar"
            else:
                city_name = city_name.strip().title()
            
            if city_name != (ship.city.city_name if ship.city else ""):
                self.stats['standardized'] += 1

            # Customer
            cust_id = default_customer_info['id']
            cust_name = default_customer_info['name']
            if ship.customer:
                cust_id = ship.customer.customer_id
                cust_name = ship.customer.customer_name or default_customer_info['name']
            else:
                self.stats['nulls_handled'] += 1

            # Driver
            driver_id = default_driver_info['id']
            driver_name = default_driver_info['name']
            driver_phone = default_driver_info['phone']
            driver_license = default_driver_info['license']
            driver_status = default_driver_info['status']
            if ship.driver:
                driver_id = ship.driver.driver_id
                driver_name = ship.driver.driver_name or default_driver_info['name']
                driver_phone = ship.driver.phone or default_driver_info['phone']
                driver_license = ship.driver.license_number or default_driver_info['license']
                driver_status = ship.driver.status or default_driver_info['status']
            else:
                self.stats['nulls_handled'] += 1

            # Vehicle
            veh_id = default_vehicle_info['id']
            veh_type = default_vehicle_info['type']
            veh_plate = default_vehicle_info['plate']
            veh_fuel = default_vehicle_info['fuel']
            veh_maint = default_vehicle_info['maintenance']
            veh_status = default_vehicle_info['status']
            if ship.vehicle:
                veh_id = ship.vehicle.vehicle_id
                veh_type = ship.vehicle.vehicle_type or default_vehicle_info['type']
                veh_plate = ship.vehicle.license_plate or default_vehicle_info['plate']
                veh_fuel = ship.vehicle.fuel_consumption
                veh_maint = ship.vehicle.maintenance_cost
                veh_status = ship.vehicle.status or default_vehicle_info['status']
            else:
                self.stats['nulls_handled'] += 1

            # Standarisasi Status Pengiriman
            status = ship.status.strip() if ship.status else 'Delivered'
            status_lower = status.lower()
            if status_lower in ['dlv', 'delivered', 'selesai', 'sampai']:
                status = 'Delivered'
            elif status_lower in ['trn', 'in transit', 'jalan', 'proses', 'transit']:
                status = 'In Transit'
            elif status_lower in ['can', 'cancelled', 'batal']:
                status = 'Cancelled'
            else:
                status = 'Delivered'

            if status != ship.status:
                self.stats['standardized'] += 1

            # Validasi Tanggal
            ship_date = ship.shipment_date
            if not ship_date:
                ship_date = timezone.now()
                self.stats['nulls_handled'] += 1
            elif ship_date > timezone.now():
                # Masa depan dibatasi ke waktu sekarang
                ship_date = timezone.now()
                self.stats['standardized'] += 1

            # --- 3. TRANSFORMATION (PENGAYAAN DATA) ---
            # Hitung lama pengiriman jika kosong (kecepatan rata-rata diasumsikan 50 km/jam)
            time_hours = ship.delivery_time_hours
            if time_hours is None or time_hours <= 0:
                time_hours = max(1, int(ship.distance_km / 50.0))
                self.stats['nulls_handled'] += 1

            # Hitung biaya jika kosong (jarak * Rp 5.000 + biaya tetap Rp 50.000)
            cost = ship.delivery_cost
            if cost is None or cost <= 0:
                cost = int(ship.distance_km * 5000 + 50000)
                self.stats['nulls_handled'] += 1

            # Kategori Keterlambatan
            is_ontime = True
            if ship.delay_minutes > 15:
                is_ontime = False

            cleaned_records.append({
                'city_name': city_name,
                'customer_id': cust_id,
                'customer_name': cust_name,
                'driver_id': driver_id,
                'driver_name': driver_name,
                'driver_phone': driver_phone,
                'driver_license': driver_license,
                'driver_status': driver_status,
                'vehicle_id': veh_id,
                'vehicle_type': veh_type,
                'vehicle_plate': veh_plate,
                'vehicle_fuel': veh_fuel,
                'vehicle_maint': veh_maint,
                'vehicle_status': veh_status,
                'shipment_date': ship_date,
                'delivery_cost': cost,
                'delivery_time_hours': time_hours,
                'distance_km': ship.distance_km,
                'delay_minutes': ship.delay_minutes,
                'is_ontime': is_ontime,
                'status': status
            })

        logger.info(f"Clean & Transform: Berhasil memproses {len(cleaned_records)} data bersih (Deduplikasi memotong {self.stats['duplicates_removed']} data).")
        return cleaned_records

    def load(self, cleaned_data):
        """
        Load: Memasukkan data terintegrasi ke dalam skema Star Schema (DWH).
        """
        loaded_count = 0
        
        # Cache lokal untuk meningkatkan kecepatan eksekusi
        city_cache = {}
        cust_cache = {}
        driver_cache = {}
        vehicle_cache = {}
        time_cache = {}

        # Pastikan data default di database warehouse untuk penanganan NULL
        # DimCity default
        def_city, _ = DimCity.objects.get_or_create(city_name="Jakarta")
        city_cache["Jakarta"] = def_city

        # DimCustomer default
        def_cust, _ = DimCustomer.objects.get_or_create(
            customer_id="C_UNK",
            defaults={'customer_name': "Unknown Customer", 'city': "Jakarta", 'city_id': def_city}
        )
        cust_cache["C_UNK"] = def_cust

        # DimDriver default
        def_driver, _ = DimDriver.objects.get_or_create(
            driver_id="D_UNK",
            defaults={'driver_name': "Unknown Driver", 'phone': "-", 'license_number': "-", 'status': "Active"}
        )
        driver_cache["D_UNK"] = def_driver

        # DimVehicle default
        def_veh, _ = DimVehicle.objects.get_or_create(
            vehicle_id="V_UNK",
            defaults={'vehicle_type': "Unknown Vehicle", 'license_plate': "-", 'fuel_consumption': 10.0, 'maintenance_cost': 0.0, 'status': "Active"}
        )
        vehicle_cache["V_UNK"] = def_veh

        for r in cleaned_data:
            # 1. Load/Get DimCity
            city_name = r['city_name']
            if city_name not in city_cache:
                city_obj, _ = DimCity.objects.get_or_create(city_name=city_name)
                city_cache[city_name] = city_obj
            city = city_cache[city_name]

            # 2. Load/Get DimCustomer
            cust_id = r['customer_id']
            if cust_id not in cust_cache:
                cust_obj, _ = DimCustomer.objects.get_or_create(
                    customer_id=cust_id,
                    defaults={'customer_name': r['customer_name'], 'city': city.city_name, 'city_id': city}
                )
                cust_cache[cust_id] = cust_obj
            cust = cust_cache[cust_id]

            # 3. Load/Get DimDriver
            drv_id = r['driver_id']
            if drv_id not in driver_cache:
                drv_obj, _ = DimDriver.objects.get_or_create(
                    driver_id=drv_id,
                    defaults={'driver_name': r['driver_name'], 'phone': r['driver_phone'], 'license_number': r['driver_license'], 'status': r['driver_status']}
                )
                driver_cache[drv_id] = drv_obj
            driver = driver_cache[drv_id]

            # 4. Load/Get DimVehicle
            veh_id = r['vehicle_id']
            if veh_id not in vehicle_cache:
                veh_obj, _ = DimVehicle.objects.get_or_create(
                    vehicle_id=veh_id,
                    defaults={'vehicle_type': r['vehicle_type'], 'license_plate': r['vehicle_plate'], 'fuel_consumption': r['vehicle_fuel'], 'maintenance_cost': r['vehicle_maint'], 'status': r['vehicle_status']}
                )
                vehicle_cache[veh_id] = veh_obj
            vehicle = vehicle_cache[veh_id]

            # 5. Load/Get DimTime
            ship_date = r['shipment_date']
            date_only = ship_date.date()
            date_str = str(date_only)
            
            if date_str not in time_cache:
                time_obj = DimTime.objects.filter(date=date_only).first()
                if not time_obj:
                    # Hitung ID secara manual jika tabel tidak auto_increment
                    max_time_id = DimTime.objects.aggregate(max_id=Max('time_id'))['max_id'] or 0
                    next_time_id = max_time_id + 1
                    
                    month_name = date_only.strftime("%B")
                    quarter = (date_only.month - 1) // 3 + 1
                    time_obj = DimTime.objects.create(
                        time_id=next_time_id,
                        date=date_only,
                        month=date_only.month,
                        year=date_only.year,
                        day=date_only.day,
                        quarter=quarter,
                        month_name=month_name
                    )
                time_cache[date_str] = time_obj
            time_dim = time_cache[date_str]

            # 6. Load FactDelivery
            # Cek apakah transaksi sudah ada di warehouse
            exists = FactDelivery.objects.filter(
                customer=cust,
                driver=driver,
                vehicle=vehicle,
                time=time_dim,
                city=city,
                delivery_cost=r['delivery_cost'],
                distance_km=r['distance_km']
            ).exists()

            if not exists:
                # Hitung ID secara manual untuk FactDelivery jika tabel tidak auto_increment
                max_del_id = FactDelivery.objects.aggregate(max_id=Max('delivery_id'))['max_id'] or 0
                next_del_id = max_del_id + 1
                
                FactDelivery.objects.create(
                    delivery_id=next_del_id,
                    customer=cust,
                    driver=driver,
                    vehicle=vehicle,
                    time=time_dim,
                    city=city,
                    delivery_cost=r['delivery_cost'],
                    delivery_time_hours=r['delivery_time_hours'],
                    distance_km=r['distance_km'],
                    delay_minutes=r['delay_minutes'],
                    is_ontime=r['is_ontime'],
                    status=r['status']
                )
                loaded_count += 1

        self.stats['loaded'] = loaded_count
        logger.info(f"Load: Berhasil memuat {loaded_count} data transaksi baru ke fact_delivery (DWH).")
