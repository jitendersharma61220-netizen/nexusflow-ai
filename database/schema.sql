-- NexusFlow AI — Supabase / Postgres schema
-- Run this in the Supabase SQL editor (Project -> SQL Editor -> New query).

create extension if not exists "uuid-ossp";

create table if not exists business_clients (
    id uuid primary key default uuid_generate_v4(),
    business_name text not null,
    project_name text not null,
    contact_name text,
    phone text,
    email text,
    created_at timestamptz not null default now()
);

create table if not exists client_projects (
    id uuid primary key default uuid_generate_v4(),
    client_id uuid references business_clients(id) on delete cascade,
    project_name text not null,
    location text,
    property_type text,
    price_range text,
    inventory jsonb,
    amenities jsonb,
    possession text,
    rera_number text,
    brochure_url text,
    created_at timestamptz not null default now()
);

create table if not exists leads (
    id uuid primary key default uuid_generate_v4(),
    client_id uuid references business_clients(id) on delete set null,
    project_id uuid references client_projects(id) on delete set null,
    name text,
    phone text,
    email text,
    budget text,
    property_type text,
    configuration text,
    preferred_location text,
    purchase_timeline text,
    intent_score integer not null default 0 check (intent_score between 0 and 100),
    lead_status text not null default 'cold' check (lead_status in ('hot','warm','cold')),
    ready_for_visit boolean not null default false,
    source text not null default 'whatsapp_demo',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists chat_messages (
    id uuid primary key default uuid_generate_v4(),
    lead_id uuid references leads(id) on delete cascade,
    role text not null check (role in ('user','assistant','system')),
    message text not null,
    timestamp timestamptz not null default now()
);

create index if not exists idx_leads_client on leads(client_id);
create index if not exists idx_leads_status on leads(lead_status);
create index if not exists idx_chat_lead on chat_messages(lead_id);
