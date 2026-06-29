import duckdb
conn = duckdb.connect("warehouse/hr_analytics.duckdb")
print("Connected.")
try:
    print("Querying performance_reviews...")
    r = conn.execute("SELECT MAX(review_period) FROM performance_reviews WHERE review_period IS NOT NULL").fetchone()
    print("performance_reviews max:", r)
except Exception as e:
    print("Error performance_reviews:", e)

try:
    print("Querying learning_enrollments...")
    r = conn.execute("SELECT MAX(completion_date) FROM learning_enrollments WHERE completion_date IS NOT NULL").fetchone()
    print("learning_enrollments max:", r)
except Exception as e:
    print("Error learning_enrollments:", e)

conn.close()
print("Done.")
