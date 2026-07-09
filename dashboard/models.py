from django.db import models

class DimCity(models.Model):
    city_id = models.AutoField(primary_key=True)
    city_name = models.CharField(max_length=100)

    class Meta:
        managed = True
        db_table = 'dim_city'

class DimCustomer(models.Model):
    customer_id = models.CharField(primary_key=True, max_length=10)
    customer_name = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    city_id = models.ForeignKey(DimCity, on_delete=models.DO_NOTHING, db_column='city_id', null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'dim_customer'

class DimDriver(models.Model):
    driver_id = models.CharField(primary_key=True, max_length=10)
    driver_name = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    license_number = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, default='Active')

    class Meta:
        managed = True
        db_table = 'dim_driver'

class DimTime(models.Model):
    time_id = models.IntegerField(primary_key=True)
    date = models.DateField(null=True, blank=True)
    month = models.IntegerField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    day = models.IntegerField(null=True, blank=True)
    quarter = models.IntegerField(null=True, blank=True)
    month_name = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'dim_time'

class DimVehicle(models.Model):
    vehicle_id = models.CharField(primary_key=True, max_length=10)
    vehicle_type = models.CharField(max_length=50, null=True, blank=True)
    license_plate = models.CharField(max_length=20, null=True, blank=True)
    fuel_consumption = models.FloatField(default=10)
    maintenance_cost = models.FloatField(default=0)
    status = models.CharField(max_length=20, default='Active')

    class Meta:
        managed = True
        db_table = 'dim_vehicle'

class FactDelivery(models.Model):
    delivery_id = models.IntegerField(primary_key=True)
    customer = models.ForeignKey(DimCustomer, on_delete=models.DO_NOTHING, db_column='customer_id', null=True, blank=True)
    driver = models.ForeignKey(DimDriver, on_delete=models.DO_NOTHING, db_column='driver_id', null=True, blank=True)
    vehicle = models.ForeignKey(DimVehicle, on_delete=models.DO_NOTHING, db_column='vehicle_id', null=True, blank=True)
    time = models.ForeignKey(DimTime, on_delete=models.DO_NOTHING, db_column='time_id', null=True, blank=True)
    city = models.ForeignKey(DimCity, on_delete=models.DO_NOTHING, db_column='city_id', null=True, blank=True)
    
    delivery_cost = models.IntegerField(null=True, blank=True)
    delivery_time_hours = models.IntegerField(null=True, blank=True)
    distance_km = models.FloatField(default=0)
    delay_minutes = models.FloatField(default=0)
    is_ontime = models.BooleanField(default=True)
    status = models.CharField(max_length=20, default='Delivered')

    class Meta:
        managed = True
        db_table = 'fact_delivery'


# ==========================================
# OPERATIONAL DATABASE MODELS (OLTP SCHEMA)
# ==========================================

class OpCity(models.Model):
    city_id = models.AutoField(primary_key=True)
    city_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'op_city'


class OpCustomer(models.Model):
    customer_id = models.CharField(primary_key=True, max_length=10)
    customer_name = models.CharField(max_length=100, null=True, blank=True)
    city = models.ForeignKey(OpCity, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'op_customer'


class OpDriver(models.Model):
    driver_id = models.CharField(primary_key=True, max_length=10)
    driver_name = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    license_number = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, default='Active')

    class Meta:
        db_table = 'op_driver'


class OpVehicle(models.Model):
    vehicle_id = models.CharField(primary_key=True, max_length=10)
    vehicle_type = models.CharField(max_length=50, null=True, blank=True)
    license_plate = models.CharField(max_length=20, null=True, blank=True)
    fuel_consumption = models.FloatField(default=10)
    maintenance_cost = models.FloatField(default=0)
    status = models.CharField(max_length=20, default='Active')

    class Meta:
        db_table = 'op_vehicle'


class OpShipment(models.Model):
    shipment_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(OpCustomer, on_delete=models.SET_NULL, null=True, blank=True)
    driver = models.ForeignKey(OpDriver, on_delete=models.SET_NULL, null=True, blank=True)
    vehicle = models.ForeignKey(OpVehicle, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(OpCity, on_delete=models.SET_NULL, null=True, blank=True)
    
    shipment_date = models.DateTimeField(null=True, blank=True)
    delivery_cost = models.IntegerField(null=True, blank=True)
    delivery_time_hours = models.IntegerField(null=True, blank=True)
    distance_km = models.FloatField(default=0)
    delay_minutes = models.FloatField(default=0)
    status = models.CharField(max_length=20, default='Delivered')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'op_shipment'

