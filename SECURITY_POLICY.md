# Política Estrita de Segurança SaaS

## 1. Objetivo e alcance

Esta política define controles obrigatórios para qualquer funcionalidade SaaS
adicionada ao Analisador de Oportunidades, especialmente pagamentos, webhooks,
persistência multi-tenant, perfis e funções administrativas.

Os controles seguem **default deny**: a ausência de uma autorização explícita,
de uma assinatura válida, de um plano oficial ou de um contexto de tenant
válido deve encerrar a operação sem produzir efeitos colaterais.

O projeto ainda não oferece faturamento ou persistência multi-tenant em
produção. O pacote `src/security/` é a fronteira de referência executável que
deverá ser reutilizada ou substituída por controles equivalentes antes de
expor essas funções. Ele não é montado na API analítica v1 e não altera o
`SCORE-0.1.0`, os contratos v1.1.0 ou o SDK existente.

## 2. As quatro Regras de Ouro

### Regra 1 — Zero confiança no cliente para preços e planos

- O cliente pode selecionar apenas um identificador de plano.
- Preço, moeda, período, descontos, limites e permissões são resolvidos no
  servidor a partir do banco de dados ou de configuração oficial versionada.
- Campos como `price`, `amount`, `currency`, `role`, `entitlements` ou similares
  recebidos do cliente devem ser rejeitados pelo schema.
- Um identificador de plano ausente do catálogo oficial deve ser recusado.
- A confirmação do provedor de pagamento deve ser reconciliada novamente com
  os valores oficiais antes de liberar qualquer benefício.

### Regra 2 — Assinatura obrigatória em todos os webhooks

- Todo endpoint de webhook deve validar uma assinatura HMAC ou o mecanismo
  criptográfico oficial do provedor antes de interpretar ou processar o evento.
- A assinatura deve cobrir o corpo bruto exato e um timestamp autenticado.
- Comparações de assinatura devem usar uma função resistente a timing attacks.
- Assinaturas ausentes, inválidas, expiradas ou aplicadas a um corpo alterado
  devem retornar HTTP `401` e não podem provocar efeitos colaterais.
- Secrets devem vir de um gerenciador de segredos ou variável protegida. Nunca
  podem ser enviados ao cliente, registrados em logs ou gravados no Git.
- IDs de evento devem ser persistidos para idempotência quando webhooks reais
  forem integrados.

### Regra 3 — Isolamento estrito de tenant em todas as consultas

- `tenant_id`, `user_id` e privilégios devem ser derivados de uma sessão ou
  token validado pelo servidor, nunca aceitos como autoridade no payload.
- Toda operação de leitura, criação, alteração e exclusão deve incluir o tenant
  autenticado no filtro da consulta.
- Acesso cruzado deve responder como recurso inexistente (`404`) para não
  confirmar a existência de dados de outro tenant.
- PostgreSQL deve usar Row Level Security como segunda barreira, com política
  **default deny**, `USING` para leitura/seleção e `WITH CHECK` para escrita.
- O usuário da aplicação não pode ser superuser, proprietário das tabelas nem
  possuir `BYPASSRLS`; tabelas sensíveis devem usar `FORCE ROW LEVEL SECURITY`.
- Jobs, exports, filas e rotinas administrativas também devem transportar e
  validar o contexto de tenant.

Exemplo conceitual para uma futura tabela PostgreSQL:

```sql
ALTER TABLE resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE resources FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_resources ON resources
USING (tenant_id = current_setting('app.tenant_id', true))
WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
```

### Regra 4 — Entrada estrita e sem mass assignment

- Todo endpoint deve usar DTO/schema com lista explícita de campos e rejeitar
  campos extras.
- Modelos de transporte não podem ser modelos de banco de dados reutilizados.
- Campos controlados pelo servidor — como `tenant_id`, `role`, `is_admin`,
  preço, permissões e status de pagamento — nunca podem ser atualizados por
  atribuição genérica do payload.
- A autorização deve ser verificada no nível do objeto e da função, mesmo
  quando a interface não exibe a operação.
- Respostas também devem expor somente os campos necessários.

## 3. Matriz mínima de testes de segurança

| Ameaça | Controle obrigatório | Resultado esperado |
| --- | --- | --- |
| Bypass de preço | Catálogo oficial no servidor + schema estrito | Preço adulterado ou plano desconhecido: `422` |
| Webhook forjado | HMAC sobre timestamp e corpo bruto | Assinatura ausente/inválida/expirada: `401` |
| IDOR entre tenants | Identidade da sessão + filtro de tenant em todo CRUD | Recurso de outro tenant: `404`, sem alteração |
| Escalação de privilégio | Allowlist de campos editáveis | `role`/`is_admin` no payload: `422` |

Os testes automatizados correspondentes ficam em `tests/security/`. Nenhuma
entrega que introduza pagamentos, webhooks, persistência ou administração pode
remover, enfraquecer ou ignorar esses testes.

## 4. Requisitos para produção

Antes de ativar funcionalidades SaaS reais:

1. substituir autenticação de teste por validação de JWT/sessão com rotação,
   expiração, issuer e audience;
2. usar PostgreSQL com RLS e testes executados também contra o banco real;
3. integrar a biblioteca oficial do provedor de pagamentos e sua política de
   replay/idempotência;
4. armazenar secrets fora do repositório e definir rotação e revogação;
5. registrar decisões de autorização sem incluir tokens, secrets ou payloads
   financeiros sensíveis;
6. executar testes negativos para todos os métodos HTTP e papéis existentes.

## 5. Referências primárias

- [OWASP API1:2023 — Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
- [OWASP API3:2023 — Broken Object Property Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/)
- [OWASP API5:2023 — Broken Function Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/)
- [Stripe — Receive webhook events](https://docs.stripe.com/webhooks)
- [PostgreSQL — Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
