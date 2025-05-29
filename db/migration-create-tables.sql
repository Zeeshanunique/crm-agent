create table public.customers (
  "Customer ID" bigint not null,
  "Country" text null,
  "Name" text null,
  "Email" text null,
  constraint customers_pkey primary key ("Customer ID")
) TABLESPACE pg_default;

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;

create table public.transactions (
  "Invoice" bigint not null,
  "InvoiceDate" timestamp with time zone null,
  "StockCode" text not null,
  "Quantity" bigint null,
  "Price" double precision null,
  "TotalPrice" double precision null,
  "Customer ID" bigint null,
  constraint transactions_pkey primary key ("Invoice", "StockCode")
) TABLESPACE pg_default;

ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

create table public.items (
  "StockCode" text not null,
  "Description" text null,
  "Price" double precision null,
  constraint items_pkey primary key ("StockCode")
) TABLESPACE pg_default;

ALTER TABLE items ENABLE ROW LEVEL SECURITY;

create table public.rfm (
  "Customer ID" bigint not null,
  recency bigint null,
  frequency bigint null,
  monetary double precision null,
  "R" bigint null,
  "F" bigint null,
  "M" bigint null,
  "RFM_Score" bigint null,
  "Segment" text null,
  constraint rfm_pkey primary key ("Customer ID")
) TABLESPACE pg_default;

ALTER TABLE rfm ENABLE ROW LEVEL SECURITY;

CREATE TABLE marketing_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('loyalty', 'referral', 're-engagement')),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE marketing_campaigns ENABLE ROW LEVEL SECURITY;

CREATE TABLE campaign_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
    customer_id BIGINT REFERENCES customers("Customer ID") ON DELETE CASCADE,
    subject TEXT,
    body TEXT,
    sent_at TIMESTAMP DEFAULT NOW(),
    status TEXT CHECK (status IN ('sent', 'bounced', 'opened', 'clicked')) DEFAULT 'sent',
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP
);

ALTER TABLE campaign_emails ENABLE ROW LEVEL SECURITY;
