-- Migration 0092: Adicionar 'completed' ao check constraint de status da tabela clients
ALTER TABLE clients DROP CONSTRAINT IF EXISTS clients_status_check;
ALTER TABLE clients ADD CONSTRAINT clients_status_check CHECK (status IN ('onboarding', 'active', 'paused', 'completed', 'archived'));
