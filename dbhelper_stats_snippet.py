
def get_dashboard_stats():
    conn = get_connection()
    stats = {}
    
    try:
        # 1. Appointment Counts by Status
        query_status = """
            SELECT APPROVAL_STATUS, COUNT(*) as count 
            FROM APPOINTMENT 
            GROUP BY APPROVAL_STATUS
        """
        status_counts = fetch_all(query_status)
        stats['status_counts'] = {row['APPROVAL_STATUS']: row['count'] for row in status_counts}
        
        # Ensure all keys exist
        for status in ['Pending', 'Approved', 'Disapproved']:
            if status not in stats['status_counts']:
                stats['status_counts'][status] = 0

        # 2. Total Revenue (Approved appointments only)
        query_revenue = """
            SELECT SUM(TOTAL_PRICE) as total_revenue
            FROM APPOINTMENT
            WHERE APPROVAL_STATUS = 'Approved'
        """
        revenue_result = fetch_one(query_revenue)
        stats['total_revenue'] = revenue_result['total_revenue'] if revenue_result and revenue_result['total_revenue'] else 0

        # 3. Monthly Revenue (Current Year)
        current_year = datetime.now().year
        query_monthly = """
            SELECT strftime('%m', SCHEDULE.SCHED_DATETIME) as month, SUM(APPOINTMENT.TOTAL_PRICE) as revenue
            FROM APPOINTMENT
            JOIN SCHEDULE ON APPOINTMENT.SCHED_ID = SCHEDULE.SCHED_ID
            WHERE APPOINTMENT.APPROVAL_STATUS = 'Approved' 
            AND strftime('%Y', SCHEDULE.SCHED_DATETIME) = ?
            GROUP BY month
            ORDER BY month
        """
        monthly_revenue = fetch_all(query_monthly, (str(current_year),))
        stats['monthly_revenue'] = {int(row['month']): row['revenue'] for row in monthly_revenue}
        
        # Fill missing months
        for m in range(1, 13):
            if m not in stats['monthly_revenue']:
                stats['monthly_revenue'][m] = 0

        # 4. Service Distribution (Top 5 popular services)
        query_services = """
            SELECT SERVICE.SERVICE_NAME, COUNT(APPOINTMENT.APPOINT_ID) as count
            FROM APPOINTMENT
            JOIN SERVICE ON APPOINTMENT.SERVICE_ID = SERVICE.SERVICE_ID
            GROUP BY SERVICE.SERVICE_NAME
            ORDER BY count DESC
            LIMIT 5
        """
        service_stats = fetch_all(query_services)
        stats['top_services'] = {row['SERVICE_NAME']: row['count'] for row in service_stats}

    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        stats = {
            'status_counts': {'Pending': 0, 'Approved': 0, 'Disapproved': 0},
            'total_revenue': 0,
            'monthly_revenue': {m: 0 for m in range(1, 13)},
            'top_services': {}
        }
    finally:
        conn.close()
        
    return stats
