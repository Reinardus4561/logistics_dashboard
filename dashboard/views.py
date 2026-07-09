from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Avg, Max
from .models import FactDelivery, DimCity, DimDriver, DimVehicle, DimTime
import json
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment

# ReportLab imports for PDF Export
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

def index(request):
    """
    Menampilkan halaman utama Dashboard Business Intelligence.
    Menghitung KPI, Filter, dan menyiapkan data untuk 10 Chart.js.
    """
    # ==========================
    # 1. Handle Filters
    # ==========================
    qs = FactDelivery.objects.all()
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    city = request.GET.get('city')
    driver = request.GET.get('driver')
    vehicle = request.GET.get('vehicle')
    status = request.GET.get('status')
    
    if start_date:
        qs = qs.filter(time__date__gte=start_date)
    if end_date:
        qs = qs.filter(time__date__lte=end_date)
    if city:
        qs = qs.filter(city__city_name=city)
    if driver:
        qs = qs.filter(driver__driver_name=driver)
    if vehicle:
        qs = qs.filter(vehicle__vehicle_type=vehicle)
    if status:
        qs = qs.filter(status=status)
        
    # Option lists for filter dropdowns
    filter_options = {
        'cities': DimCity.objects.all(),
        'drivers': DimDriver.objects.all(),
        'vehicles': DimVehicle.objects.values('vehicle_type').distinct()
    }

    # ==========================
    # 2. Hitung KPI Dashboard
    # ==========================
    kpi = {
        'total_pengiriman': qs.count(),
        'total_biaya': qs.aggregate(total=Sum('delivery_cost'))['total'] or 0,
        'total_driver': qs.values('driver').distinct().count(),
        'total_kendaraan': qs.values('vehicle').distinct().count(),
        'total_customer': qs.values('customer').distinct().count(),
        'rata_waktu': qs.aggregate(rata=Avg('delivery_time_hours'))['rata'] or 0,
        'tepat_waktu': qs.filter(is_ontime=True).count(),
        'terlambat': qs.filter(is_ontime=False).count(),
    }

    # ==========================
    # 3. Persiapkan Data 10 Visualisasi
    # ==========================
    
    # C1. Delivery Cost per Kota (Bar)
    c1_qs = qs.values('city__city_name').annotate(total=Sum('delivery_cost')).order_by('-total')
    c1_labels = [i['city__city_name'] for i in c1_qs]
    c1_data = [i['total'] for i in c1_qs]

    # C2. Jumlah Pengiriman per Kota (Pie)
    c2_qs = qs.values('city__city_name').annotate(total=Count('delivery_id')).order_by('-total')
    c2_labels = [i['city__city_name'] for i in c2_qs]
    c2_data = [i['total'] for i in c2_qs]

    # C3. Performa Driver (Top 5 - Jumlah Kirim)
    c3_qs = qs.values('driver__driver_name').annotate(total=Count('delivery_id')).order_by('-total')[:5]
    c3_labels = [i['driver__driver_name'] for i in c3_qs]
    c3_data = [i['total'] for i in c3_qs]

    # C4. Performa Kendaraan (Avg Time)
    c4_qs = qs.values('vehicle__vehicle_type').annotate(rata=Avg('delivery_time_hours')).order_by('rata')
    c4_labels = [i['vehicle__vehicle_type'] for i in c4_qs]
    c4_data = [float(i['rata']) if i['rata'] else 0 for i in c4_qs]

    # C5. Distribusi Jenis Kendaraan (Count)
    c5_qs = qs.values('vehicle__vehicle_type').annotate(total=Count('delivery_id')).order_by('-total')
    c5_labels = [i['vehicle__vehicle_type'] for i in c5_qs]
    c5_data = [i['total'] for i in c5_qs]

    # C6. Delivery Status (Pie)
    c6_qs = qs.values('status').annotate(total=Count('delivery_id'))
    c6_labels = [i['status'] for i in c6_qs]
    c6_data = [i['total'] for i in c6_qs]

    # C7. Delivery Time Trend (Line - Daily)
    c7_qs = qs.values('time__date').annotate(rata=Avg('delivery_time_hours')).order_by('time__date')[:30]
    c7_labels = [str(i['time__date']) for i in c7_qs if i['time__date']]
    c7_data = [float(i['rata']) for i in c7_qs if i['time__date']]

    # C8. Top 10 Kota (By Cost)
    c8_labels = c1_labels[:10]
    c8_data = c1_data[:10]

    # C9. Top Driver by Cost generated
    c9_qs = qs.values('driver__driver_name').annotate(total=Sum('delivery_cost')).order_by('-total')[:10]
    c9_labels = [i['driver__driver_name'] for i in c9_qs]
    c9_data = [i['total'] for i in c9_qs]

    # C10. Monthly Delivery Vol
    c10_qs = qs.values('time__month_name').annotate(total=Count('delivery_id'))
    c10_labels = [i['time__month_name'] for i in c10_qs if i['time__month_name']]
    c10_data = [i['total'] for i in c10_qs if i['time__month_name']]

    # C11. Yearly Delivery Vol (Roll-up)
    c11_qs = qs.values('time__year').annotate(total=Count('delivery_id')).order_by('time__year')
    c11_labels = [str(i['time__year']) for i in c11_qs if i['time__year']]
    c11_data = [i['total'] for i in c11_qs if i['time__year']]

    charts_json = {
        'c1_labels': c1_labels, 'c1_data': c1_data,
        'c2_labels': c2_labels, 'c2_data': c2_data,
        'c3_labels': c3_labels, 'c3_data': c3_data,
        'c4_labels': c4_labels, 'c4_data': c4_data,
        'c5_labels': c5_labels, 'c5_data': c5_data,
        'c6_labels': c6_labels, 'c6_data': c6_data,
        'c7_labels': c7_labels, 'c7_data': c7_data,
        'c8_labels': c8_labels, 'c8_data': c8_data,
        'c9_labels': c9_labels, 'c9_data': c9_data,
        'c10_labels': c10_labels, 'c10_data': c10_data,
        'c11_labels': c11_labels, 'c11_data': c11_data,
    }

    # ==========================
    # 4. Top Performance & Map
    # ==========================
    fastest = qs.filter(delivery_time_hours__gt=0).order_by('delivery_time_hours').first()
    max_cost = qs.order_by('-delivery_cost').first()
    
    top_perf = {
        'top_driver': c3_labels[0] if c3_labels else '-',
        'top_kota': c1_labels[0] if c1_labels else '-',
        'top_kendaraan': c5_labels[0] if c5_labels else '-',
        'fastest_time': fastest.delivery_time_hours if fastest else 0,
        'max_cost': max_cost.delivery_cost if max_cost else 0,
    }

    # Map Mockup (Assigning dummy coordinates to cities)
    mockup_coords = {
        'Jakarta': {'lat': -6.2088, 'lng': 106.8456},
        'Surabaya': {'lat': -7.2504, 'lng': 112.7688},
        'Bandung': {'lat': -6.9175, 'lng': 107.6191},
        'Medan': {'lat': 3.5952, 'lng': 98.6722},
        'Makassar': {'lat': -5.1476, 'lng': 119.4327}
    }
    map_data = []
    for city, cost in zip(c1_labels[:5], c1_data[:5]):
        coords = mockup_coords.get(city, {'lat': -2.5, 'lng': 118.0}) # default center
        map_data.append({'city': city, 'cost': cost, 'lat': coords['lat'], 'lng': coords['lng']})

    # ==========================
    # 5. OLAP Pivot Table (Vehicle Type vs City Cost)
    # ==========================
    pivot_qs = qs.values('vehicle__vehicle_type', 'city__city_name').annotate(total_cost=Sum('delivery_cost'))
    pivot_cities = sorted(list(set(item['city__city_name'] for item in pivot_qs if item['city__city_name'])))
    pivot_vehicles = sorted(list(set(item['vehicle__vehicle_type'] for item in pivot_qs if item['vehicle__vehicle_type'])))
    
    # Pre-populate map
    cost_map = {}
    for veh in pivot_vehicles:
        cost_map[veh] = {}
        for cit in pivot_cities:
            cost_map[veh][cit] = 0
            
    for item in pivot_qs:
        veh = item['vehicle__vehicle_type']
        cit = item['city__city_name']
        if veh and cit:
            cost_map[veh][cit] = item['total_cost'] or 0
            
    pivot_rows = []
    for veh in pivot_vehicles:
        row_costs = []
        for cit in pivot_cities:
            row_costs.append(cost_map[veh][cit])
        pivot_rows.append({
            'vehicle': veh,
            'costs': row_costs
        })

    # ==========================
    # 6. AI Insights & Summary
    # ==========================
    total_kirim = kpi['total_pengiriman']
    delay_pct = (kpi['terlambat'] / total_kirim * 100) if total_kirim > 0 else 0
    max_cost_val = top_perf['max_cost']
    avg_time = kpi['rata_waktu']

    ai_insights = [
        f"Kota {top_perf['top_kota']} mendominasi total pengiriman dengan biaya tertinggi.",
        f"Driver {top_perf['top_driver']} memiliki performa pengiriman terbanyak.",
        f"Kendaraan {top_perf['top_kendaraan']} paling banyak digunakan untuk distribusi armada.",
        f"Rata-rata waktu pengiriman logistik adalah {avg_time:.2f} jam.",
        f"Tingkat keterlambatan pengiriman tercatat sebesar {delay_pct:.1f}% dari total armada.",
        f"Biaya pengiriman tunggal terbesar mencapai Rp {max_cost_val:,.0f}."
    ]
    
    ai_summary = f"Selama periode terpilih, terdapat {kpi['total_pengiriman']} pengiriman dengan total biaya Rp {kpi['total_biaya']:,.0f}. " \
                 f"Kota {top_perf['top_kota']} menjadi kota dengan biaya tertinggi sedangkan kendaraan " \
                 f"{top_perf['top_kendaraan']} merupakan armada yang paling banyak digunakan. Tingkat keterlambatan " \
                 f"tercatat sebanyak {kpi['terlambat']} kasus dari total ({delay_pct:.1f}%)."

    # ==========================
    # 7. Data Tables
    # ==========================
    transactions = qs.select_related('customer', 'driver', 'vehicle', 'city', 'time').order_by('-delivery_id')[:200]

    context = {
        'kpi': kpi,
        'charts_json': json.dumps(charts_json),
        'top_perf': top_perf,
        'map_json': json.dumps(map_data),
        'pivot_cities': pivot_cities,
        'pivot_vehicles': pivot_vehicles,
        'pivot_rows': pivot_rows,
        'ai_insights': ai_insights,
        'ai_summary': ai_summary,
        'transactions': transactions,
        'filter_options': filter_options
    }
    return render(request, 'dashboard/index.html', context)


def export_excel(request):
    """
    Export transaksi ke format Excel
    """
    qs = FactDelivery.objects.select_related('customer', 'driver', 'vehicle', 'city', 'time').all()[:1000] # Limit 1000 for demo
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Transaksi Logistik"
    
    # Headers
    headers = ["ID", "Tanggal", "Pelanggan", "Driver", "Kendaraan", "Kota", "Biaya", "Waktu(Jam)", "Status"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        
    # Data
    for row, t in enumerate(qs, 2):
        ws.cell(row=row, column=1, value=t.delivery_id)
        ws.cell(row=row, column=2, value=str(t.time.date) if t.time else "")
        ws.cell(row=row, column=3, value=t.customer.customer_name if t.customer else "")
        ws.cell(row=row, column=4, value=t.driver.driver_name if t.driver else "")
        ws.cell(row=row, column=5, value=t.vehicle.vehicle_type if t.vehicle else "")
        ws.cell(row=row, column=6, value=t.city.city_name if t.city else "")
        ws.cell(row=row, column=7, value=t.delivery_cost)
        ws.cell(row=row, column=8, value=t.delivery_time_hours)
        ws.cell(row=row, column=9, value=t.status)
        
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Transaksi_Logistik.xlsx'
    wb.save(response)
    return response


def ajax_drilldown(request):
    """
    Endpoint AJAX untuk proses OLAP Drill Down.
    Level 1: Kota -> Level 2: Driver -> Level 3: Kendaraan -> Level 4: Transaksi
    """
    level = request.GET.get('level', '1')
    city_name = request.GET.get('city_name', None)
    driver_name = request.GET.get('driver_name', None)
    vehicle_type = request.GET.get('vehicle_type', None)

    data = []

    if level == '2' and city_name:
        qs = FactDelivery.objects.filter(city__city_name=city_name).values('driver__driver_name').annotate(
            total_pengiriman=Count('delivery_id'), total_biaya=Sum('delivery_cost')).order_by('-total_pengiriman')
        for item in qs: data.append({'name': item['driver__driver_name'], 'total_pengiriman': item['total_pengiriman'], 'total_biaya': float(item['total_biaya'] or 0)})
    
    elif level == '3' and city_name and driver_name:
        qs = FactDelivery.objects.filter(city__city_name=city_name, driver__driver_name=driver_name).values('vehicle__vehicle_type').annotate(
            total_pengiriman=Count('delivery_id'), rata_waktu=Avg('delivery_time_hours')).order_by('-total_pengiriman')
        for item in qs: data.append({'name': item['vehicle__vehicle_type'], 'total_pengiriman': item['total_pengiriman'], 'rata_waktu': float(item['rata_waktu'] or 0)})
    
    elif level == '4' and city_name and driver_name and vehicle_type:
        qs = FactDelivery.objects.filter(city__city_name=city_name, driver__driver_name=driver_name, vehicle__vehicle_type=vehicle_type).select_related('customer', 'time').order_by('-delivery_id')[:50]
        for item in qs: data.append({'tanggal': str(item.time.date if item.time else ''), 'customer': item.customer.customer_name if item.customer else '', 'biaya': float(item.delivery_cost), 'status': item.status})
            
    else:
        qs = FactDelivery.objects.values('city__city_name').annotate(total_pengiriman=Count('delivery_id')).order_by('-total_pengiriman')
        for item in qs: data.append({'name': item['city__city_name'], 'total_pengiriman': item['total_pengiriman']})

    return JsonResponse({'status': 'success', 'data': data})


def export_pdf(request):
    """
    Mengekspor laporan Business Intelligence Logistics ke format PDF menggunakan ReportLab.
    Format Kertas A4 (Portrait) dengan Judul, Tanggal, KPI, dan Footer, dilengkapi Identitas Kelompok.
    """
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="BI_Logistics_Report.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2.0, height - 50, "Business Intelligence Logistics Analytics Report")
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width / 2.0, height - 70, "PT Smart Manufacturing Indonesia")

    # Tanggal Cetak
    p.setFont("Helvetica", 10)
    print_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    p.drawString(50, height - 100, f"Tanggal Cetak: {print_date}")
    
    # Identitas Kelompok
    p.drawString(400, height - 100, "Dibuat Oleh: Kelompok III")

    # KPI Calculation
    total_pengiriman = FactDelivery.objects.count()
    total_biaya = FactDelivery.objects.aggregate(total=Sum('delivery_cost'))['total'] or 0
    total_driver = DimDriver.objects.count()
    total_kendaraan = DimVehicle.objects.count()
    rata_waktu = FactDelivery.objects.aggregate(rata=Avg('delivery_time_hours'))['rata'] or 0

    # Ringkasan KPI
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 130, "Ringkasan KPI:")
    p.setFont("Helvetica", 11)
    kpi_y_start = height - 150
    p.drawString(70, kpi_y_start, f"- Total Pengiriman: {total_pengiriman:,} transaksi")
    p.drawString(70, kpi_y_start - 20, f"- Total Biaya Pengiriman: Rp {total_biaya:,.2f}")
    p.drawString(70, kpi_y_start - 40, f"- Total Driver: {total_driver} orang")
    p.drawString(70, kpi_y_start - 60, f"- Total Kendaraan: {total_kendaraan} unit")
    p.drawString(70, kpi_y_start - 80, f"- Rata-rata Waktu Pengiriman: {rata_waktu:.2f} jam")

    # Tabel Ringkasan (Top 5 Kota dengan Biaya Tertinggi)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, kpi_y_start - 120, "Top 5 Kota Berdasarkan Total Biaya Pengiriman:")

    top_cities = FactDelivery.objects.values('city__city_name').annotate(
        total_cost=Sum('delivery_cost'), total_kirim=Count('delivery_id')
    ).order_by('-total_cost')[:5]

    data = [["No", "Kota Tujuan", "Total Pengiriman", "Total Biaya (Rp)"]]
    for i, city in enumerate(top_cities, start=1):
        data.append([str(i), city['city__city_name'], str(city['total_kirim']), f"{city['total_cost']:,.2f}"])

    table = Table(data, colWidths=[40, 150, 120, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, kpi_y_start - 240)

    # Footer
    p.setFont("Helvetica-Oblique", 9)
    p.drawString(50, 30, "Generated by Django Business Intelligence Logistics Analytics Dashboard")

    p.showPage()
    p.save()
    return response
