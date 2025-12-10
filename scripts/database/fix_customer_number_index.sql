-- Fix customer_number unique index to allow multiple NULLs
-- This is needed for admin/operator users who don't have customer numbers

-- Drop the existing unique index
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'ix_users_customer_number' AND object_id = OBJECT_ID('users'))
BEGIN
    DROP INDEX ix_users_customer_number ON users;
    PRINT 'Dropped existing ix_users_customer_number index';
END

-- Create a filtered unique index that only enforces uniqueness for non-NULL values
CREATE UNIQUE INDEX ix_users_customer_number 
ON users (customer_number) 
WHERE customer_number IS NOT NULL;

PRINT 'Created filtered unique index ix_users_customer_number';
GO
