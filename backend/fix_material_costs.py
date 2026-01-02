"""Fix material costs from $/KG to $/G"""
from sqlalchemy import create_engine, text

# Connect directly
engine = create_engine('postgresql://filaops:filaops@localhost:5432/filaops')

with open('fix_output.txt', 'w') as f:
    with engine.connect() as conn:
        # Check current state
        result = conn.execute(text("""
            SELECT COUNT(*) as cnt
            FROM products 
            WHERE sku LIKE 'MAT-%' 
            AND unit IN ('G', 'g')
            AND standard_cost > 1
        """))
        row = result.fetchone()
        f.write(f'Found {row[0]} products to update\n')
        
        if row[0] > 0:
            # Do the update
            update_result = conn.execute(text("""
                UPDATE products 
                SET standard_cost = standard_cost / 1000,
                    average_cost = CASE WHEN average_cost IS NOT NULL THEN average_cost / 1000 ELSE NULL END,
                    last_cost = CASE WHEN last_cost IS NOT NULL THEN last_cost / 1000 ELSE NULL END
                WHERE sku LIKE 'MAT-%' 
                AND unit IN ('G', 'g')
                AND standard_cost > 1
            """))
            conn.commit()
            f.write(f'Updated {update_result.rowcount} rows\n')
        else:
            f.write('No products need updating\n')
        
        # Verify
        result = conn.execute(text("""
            SELECT sku, standard_cost 
            FROM products 
            WHERE sku = 'MAT-ABS-BAMBU_GREEN'
        """))
        row = result.fetchone()
        if row:
            f.write(f'Verification - {row[0]}: ${row[1]}/G\n')

    f.write('Done!\n')
