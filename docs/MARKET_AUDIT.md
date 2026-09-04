# Auditoría de Mercado y Oportunidad — SES Dashboard SaaS

**Fecha:** Septiembre 2026  
**Objetivo:** Evaluar la oportunidad de mercado para el SES Dashboard como producto SaaS monetizable

---

## 1. Resumen Ejecutivo

### Veredicto: **OPORTUNIDAD SÓLIDA CON DIFERENCIACIÓN CLARA**

El mercado de email deliverability está en crecimiento acelerado (CAGR 8-12%) y existe una brecha significativa entre las soluciones existentes: las opciones baratas carecen de funcionalidades avanzadas, y las completas son extremadamente caras. **SES Dashboard puede posicionarse como la solución "just right" para el segmento SMB/SME.**

---

## 2. Análisis del Mercado

### 2.1 Tamaño del Mercado

| Fuente | Mercado Actual (2025-2026) | Proyección (2030-2035) | CAGR |
|--------|---------------------------|------------------------|------|
| Business Research Insights | $1.35B (2026) | $2.8B (2035) | 8.47% |
| WiseGuy Reports | $2.64B (2025) | $5B (2035) | 6.6% |
| GII Research | $1.71B (2025) | $4.52B (2033) | 12.82% |
| The Business Research Company | $1.35B (2025) | $2.22B (2030) | 10.6% |

**Promedio ponderado:** Mercado actual ~$1.5B, proyección ~$3.5B para 2030-2033.

### 2.2 Segmentos de Mercado

| Segmento | Tamaño | Crecimiento | Relevancia para nosotros |
|----------|--------|-------------|--------------------------|
| Email Deliverability Tools | $1.35-1.71B | 9-13% | **ALTA** — Nuestro foco principal |
| Email Verification | $300-500M | 12-15% | **MEDIA** — Feature complementaria |
| Email Marketing Platforms | $14-18B | 10-14% | **BAJA** — Competidores muy grandes |

### 2.3 Drivers de Crecimiento

1. **Adopción de email marketing** — El email sigue siendo el canal con mayor ROI ($36 por cada $1 invertido)
2. **Amenazas de spam/phishing** — Crecimiento de 40% en amenazas año tras año
3. **Regulaciones de privacidad** — GDPR, CCPA exigen mejor gestión de datos
4. **IA y automatización** — 63% de adopción hoy, proyectado 75-80% para 2026
5. **Crecimiento del e-commerce** — Más transacciones = más emails = más necesidad de deliverability

---

## 3. Análisis Competitivo

### 3.1 Competidores Directos (Email Deliverability Monitoring)

| Competidor | Precio Inicio | Free Tier | Features Principales | Fortalezas | Debilidades |
|------------|---------------|-----------|----------------------|------------|-------------|
| **GlockApps** | $59/mo | 3 tests | Inbox placement, DMARC, blacklist | Líder en inbox testing | Caro para SMBs |
| **Validity Everest** | Custom ($500+/mo) | No | Suite completa enterprise | Benchmark competitivo | Precio prohibitivo SMB |
| **Litmus** | $99/mo | Trial 7 días | Rendering + spam testing | 100+ clientes email | Enfoque QA, no monitoring |
| **Mail-Tester** | Gratis | 3 tests/día | Spam score básico | Gratis, simple | Muy limitado |
| **Unspam.email** | $9/mo | 10 tests/mo | Inbox + spam + preview | Precio accesible | Relativamente nuevo |
| **MXToolbox** | Gratis (pago) | Sí | DNS + blacklist checks | Herramienta madura | Solo diagnóstico |
| **ZeroBounce** | $20 (créditos) | 100 créditos | Verificación + scoring | Buen balance features/precio | No es monitoring continuo |

### 3.2 Competidores Indirectos (Email Sending Platforms)

| Competidor | Precio Inicio | Free Tier | Market Share |
|------------|---------------|-----------|--------------|
| **AWS SES** | $0.10/1K emails | 3K/mo gratis (12 meses) | ~25% del mercado |
| **SendGrid (Twilio)** | $19.95/mo | Trial 60 días | ~20% del mercado |
| **Mailgun** | $15/mo o $1/1K | Trial | ~15% del mercado |
| **Postmark** | $15/mo | 100 emails/mo | ~10% del mercado |
| **Brevo** | Gratis (300/día) | Sí | ~8% del mercado |

### 3.3 Mapa de Posicionamiento

```
                    PRECIO ALTO
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    │   Litmus           │   Validity Everest │
    │   Email on Acid    │   (Enterprise)     │
    │                    │                    │
FUNCIONALIDADES ────────┼─────────────────── FUNCIONALIDADES
BÁSICAS                 │                    AVANZADAS
    │                    │                    │
    │   Mail-Tester      │   ★ SES Dashboard  │
    │   Unspam           │   (Nuestro)        │
    │   MXToolbox        │   GlockApps        │
    │                    │                    │
    └────────────────────┼────────────────────┘
                         │
                    PRECIO BAJO
```

---

## 4. Análisis de Precios

### 4.1 Estructura de Precios Competitiva

| Nivel | Competidores | Rango de Precio | Features Típicas |
|-------|--------------|-----------------|------------------|
| **Free/Starter** | Mail-Tester, Unspam | $0-9/mo | Tests básicos, limitados |
| **Pro** | GlockApps, Unspam | $15-59/mo | Monitoring continuo, alertas |
| **Business** | Litmus, Mailgun | $89-199/mo | API completa, soporte prioritario |
| **Enterprise** | Validity, SendGrid | $500+/mo | Suite completa, soporte dedicado |

### 4.2 Nuestra Propuesta de Valor

**Posicionamiento:** Pro a precio de Starter

| Tiers | Precio | Features | Competidor Equivalente |
|-------|--------|----------|------------------------|
| **Free** | $0 | 100 emails/mo, 1 dominio, reportes básicos | Mail-Tester (limitado) |
| **Starter** | $19/mo | 1,000 emails/mo, 3 dominios, alertas email | Unspam ($9/mo, menos features) |
| **Pro** | $49/mo | 10,000 emails/mo, dominios ilimitados, Slack, A/B testing | GlockApps ($59/mo) |
| **Business** | $149/mo | 50,000 emails/mo, API completa, soporte prioritario | Litmus ($99/mo, sin sending) |
| **Enterprise** | Custom | Custom, SLA, integraciones, soporte dedicado | Validity ($500+/mo) |

---

## 5. Análisis FODA

### 5.1 Fortalezas

1. **Costo operativo bajo** — AWS SES cobra $0.10/1K emails vs $1-19/1K de competidores
2. **Stack moderno** — FastAPI + PostgreSQL, fácil de escalar
3. **Multi-tenant desde el inicio** — Listo para SaaS
4. **Features completas** — Monitoreo, alertas, reportes, A/B testing, heatmap, verificación
5. **Open source potential** — Core open + premium features
6. **Enfoque en deliverability** — No somos un ESP generalista

### 5.2 Debilidades

1. **Sin track record** — Competidores tienen años de reputación
2. **Infraestructura limitada** — No tenemos seed lists globales como GlockApps
3. **Equipo pequeño** — Desarrollo y soporte limitado
4. **Dependencia de AWS SES** — Si AWS cambia pricing, nos afecta

### 5.3 Oportunidades

1. **Brecha de precio** — Mercado entre $10-60/mo está subatendido
2. **SMBs desatendidos** — Soluciones enterprise son demasiado caras para pymes
3. **Mercado LATAM** — Pocos competidores con soporte en español
4. **Integración con SES** — Nadie ofrece monitoreo nativo para SES
5. **Post-SendGrid** — Usuarios buscando alternativas tras eliminación de free tier
6. **IA para recomendaciones** — Potencial de diferenciación con AI insights

### 5.4 Amenazas

1. **AWS SES native monitoring** — AWS podría mejorar sus propias herramientas
2. **Competidores establecidos** — GlockApps, Litmus tienen presupuestos de marketing
3. **Cambio de algoritmos** — Gmail/Outlook cambian frecuentemente
4. **Consolidación del mercado** — Adquisiciones (ActiveCampaign compró Postmark)
5. **Regulación** — Nuevas leyes podrían cambiar la dinámica

---

## 6. Análisis de Clientes Objetivo

### 6.1 Segmentos Prioritarios

| Segmento | Tamaño | Dolor Principal | Disposición a Pagar |
|----------|--------|-----------------|---------------------|
| **Startups tech** | Alto | Deliverability crítica para growth | $20-50/mo |
| **Agencias de marketing** | Alto | Necesitan monitorear múltiples clientes | $50-150/mo |
| **E-commerce SMBs** | Muy alto | Emails transaccionales = revenue | $20-100/mo |
| **SaaS companies** | Medio | Onboarding, notificaciones | $30-80/mo |
| **Freelancers/Consultores** | Alto | Quieren parecer profesionales | $10-30/mo |

### 6.2 Buyer Persona

**"Marketing Manager Tech"**
- Empresa: 10-100 empleados
- Envía: 10K-100K emails/mes
- Stack: AWS SES o SendGrid
- Dolor: "No sé si mis emails llegan al inbox"
- Presupuesto: $30-100/mo
- Decisión: Velocidad de setup, ROI claro

---

## 7. Proyección de Ingresos

### 7.1 Escenario Conservador (Año 1)

| Métrica | Mes 3 | Mes 6 | Mes 12 |
|---------|-------|-------|--------|
| Usuarios free | 100 | 300 | 800 |
| Usuarios paid | 10 | 30 | 80 |
| MRR | $300 | $1,200 | $4,000 |
| ARR | $3,600 | $14,400 | $48,000 |

### 7.2 Escenario Optimista (Año 1)

| Métrica | Mes 3 | Mes 6 | Mes 12 |
|---------|-------|-------|--------|
| Usuarios free | 300 | 1,000 | 3,000 |
| Usuarios paid | 30 | 100 | 300 |
| MRR | $1,000 | $5,000 | $18,000 |
| ARR | $12,000 | $60,000 | $216,000 |

### 7.3 Unit Economics

| Métrica | Valor | Benchmark |
|---------|-------|-----------|
| CAC estimado | $50-100 | Industry: $100-200 |
| LTV estimado | $600-1,200 | LTV/CAC > 6x |
| Churn mensual | 5-8% | Industry: 5-7% |
| Margen bruto | 85-90% | SaaS typical: 70-80% |

---

## 8. Estrategia de Go-to-Market

### 8.1 Fase 1: Launch (Meses 1-3)

- **Canal:** Product Hunt, Hacker News, Reddit r/email, IndieHackers
- **Oferta:** Free tier generoso + 30% descuento anual
- **Contenido:** Blog posts sobre deliverability, tutoriales SES
- **Meta:** 100 usuarios free, 10 paid

### 8.2 Fase 2: Growth (Meses 4-8)

- **Canal:** SEO, YouTube tutorials, partnerships con agencies
- **Oferta:** Referral program (1 mes gratis por referido)
- **Contenido:** Comparativas con competidores, case studies
- **Meta:** 500 usuarios free, 50 paid

### 8.3 Fase 3: Scale (Meses 9-12)

- **Canal:** Paid ads (Google, LinkedIn), partnerships con ESPs
- **Oferta:** Enterprise tier con onboarding dedicado
- **Contenido:** Webinars, certifications de deliverability
- **Meta:** 2,000 usuarios free, 200 paid

---

## 9. Roadmap de Features Críticos

### 9.1 Features MVP (Ya implementadas ✅)

- [x] Multi-tenant architecture
- [x] Webhook receiver (SES/SNS)
- [x] Onboarding wizard
- [x] Alertas de deliverability
- [x] Reportes de deliverability
- [x] Email verification
- [x] A/B testing
- [x] Heatmap de engagement
- [x] Integración directa con SES
- [x] Notificaciones Slack/Email
- [x] Exportación PDF/CSV

### 9.2 Features para Lanzamiento (Q4 2026)

- [ ] Dashboard público (shareable reports)
- [ ] Integración con Mailchimp/ConvertKit
- [ ] API pública para integraciones
- [ ] White-label para agencies
- [ ] Multi-usuario con roles
- [ ] Audit log

### 9.3 Features Post-Launch (2027)

- [ ] IA para predicción de deliverability
- [ ] Warm-up automático de dominios
- [ ] Integración con CRM (HubSpot, Salesforce)
- [ ] Mobile app para alertas
- [ ] Marketplace de templates

---

## 10. Recomendaciones

### 10.1 ACCIÓN INMEDIATA

1. **Lanzar beta cerrada** — Invitar a 50 usuarios de Product Hunt/Hacker News
2. **Crear landing page** — Value prop clara: "Monitorea tu deliverability en SES por $19/mes"
3. **Documentar API** — Swagger/OpenAPI para desarrolladores
4. **Configurar billing** — Stripe para suscripciones

### 10.2 DIFERENCIACIÓN CLAVE

1. **Nativo para AWS SES** — Nadie más ofrece esto
2. **Precio accesible** — Pro features a precio de starter
3. **Setup en 5 minutos** — Onboarding wizard + verificación automática
4. **Alertas inteligentes** — No spam, solo lo importante

### 10.3 RIESGOS A MITIGAR

1. **No depender solo de SES** — Agregar soporte para otros providers
2. **Construir comunidad** — Content marketing + soporte activo
3. **Iterar rápido** — Releases semanales, feedback loop con usuarios

---

## 11. Conclusión

### **OPORTUNIDAD: 8/10**

El mercado de email deliverability tools crece a 10-13% anual y hay una clara brecha para una solución **moderna, accesible y enfocada en SES**. Los competidores son caros o carecen de features clave. 

**Nuestra ventaja competitiva:**
- Única solución nativa para AWS SES
- 80% más barata que GlockApps/Litmus
- Features completas desde el tier Starter
- Setup en minutos, no horas

**Próximos pasos críticos:**
1. Lanzar beta cerrada esta semana
2. Conseguir 10 early adopters que paguen
3. Iterar según feedback
4. Escalar a 100 usuarios paid en 3 meses

---

*Documento generado: Septiembre 2026*  
*Fuentes: Business Research Insights, WiseGuy Reports, GII Research, The Business Research Company, Verified.email, análisis de mercado*
