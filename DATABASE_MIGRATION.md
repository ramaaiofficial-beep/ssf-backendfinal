# Database Migration Guide

## ⚠️ **Issue: Donation Not Saving to Database**

If you're seeing errors like:
- `"Could not find the 'donor_email' column"`
- `"Could not find the 'paypal_order_id' column"`

This means your database schema needs to be updated.

## 🔧 **Solution: Run Database Migrations**

### Step 1: Check Your Current Schema

Go to your Supabase dashboard:
1. Navigate to **SQL Editor**
2. Run this query to check if columns exist:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'donations'
ORDER BY column_name;
```

### Step 2: Run the PayPal Fields Migration

If the PayPal columns are missing, run this migration:

```sql
-- Add PayPal-specific columns to donations table
ALTER TABLE donations 
  ADD COLUMN IF NOT EXISTS paypal_order_id TEXT,
  ADD COLUMN IF NOT EXISTS paypal_capture_id TEXT,
  ADD COLUMN IF NOT EXISTS paypal_payer_id TEXT,
  ADD COLUMN IF NOT EXISTS paypal_payment_details JSONB;

-- Add indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_donations_paypal_order_id ON donations(paypal_order_id);
CREATE INDEX IF NOT EXISTS idx_donations_paypal_capture_id ON donations(paypal_capture_id);
CREATE INDEX IF NOT EXISTS idx_donations_paypal_payer_id ON donations(paypal_payer_id);
```

### Step 3: Verify donor_email Column Exists

If `donor_email` is missing, add it:

```sql
ALTER TABLE donations 
  ADD COLUMN IF NOT EXISTS donor_email TEXT;
```

### Step 4: Run Full Schema (If Needed)

If your database is missing multiple columns, you may need to run the full production schema:

1. Go to Supabase Dashboard → SQL Editor
2. Copy the contents of `PRODUCTION_SCHEMA.sql`
3. Run it in the SQL Editor

**Note:** This will create all tables and columns if they don't exist.

## ✅ **Quick Fix: Run All Migrations at Once**

Run this in your Supabase SQL Editor:

```sql
-- Ensure all required columns exist
ALTER TABLE donations 
  ADD COLUMN IF NOT EXISTS donor_email TEXT,
  ADD COLUMN IF NOT EXISTS paypal_order_id TEXT,
  ADD COLUMN IF NOT EXISTS paypal_capture_id TEXT,
  ADD COLUMN IF NOT EXISTS paypal_payer_id TEXT,
  ADD COLUMN IF NOT EXISTS paypal_payment_details JSONB;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_donations_paypal_order_id ON donations(paypal_order_id);
CREATE INDEX IF NOT EXISTS idx_donations_paypal_capture_id ON donations(paypal_capture_id);
CREATE INDEX IF NOT EXISTS idx_donations_paypal_payer_id ON donations(paypal_payer_id);
```

## 🔍 **Verify Migration Worked**

After running migrations, test by making a donation. Check the backend logs - you should see:
```
Donation record saved: SSLF-xxxxxx
```

If you still see errors, check:
1. RLS (Row Level Security) policies allow inserts
2. Service role key has proper permissions
3. All required columns exist

## 📝 **Note**

The backend code has been updated to handle missing PayPal columns gracefully, but `donor_email` is a standard column that should exist in your schema.

