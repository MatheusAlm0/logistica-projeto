# Previsor de Atrasos Logísticos — Visão do Produto

## O que é

O **Previsor de Atrasos Logísticos** é uma plataforma SaaS de gestão e inteligência logística. Empresas de e-commerce e transportadoras a utilizam para cadastrar entregas, receber previsões automáticas de risco de atraso, rastrear pacotes em tempo real e treinar modelos de machine learning com dados reais de operação.

---

## Para quem é

| Perfil | Quem é | O que faz na plataforma |
|---|---|---|
| **Admin** | Equipe técnica / operações da plataforma | Gerencia usuários, dispara retreinos manuais, acompanha o ciclo de aprendizado do modelo |
| **Empresa** | Lojistas, transportadoras e distribuidoras | Cadastra entregas, registra checkpoints em galpões, consulta previsões de risco |
| **Cliente final** | Consumidor que aguarda a entrega | Rastreia o pacote pelo código sem precisar de login |

O acesso é isolado por empresa: cada lojista vê somente as suas próprias entregas.

---

## O que o sistema faz

### Previsão de risco de atraso
Ao cadastrar uma entrega, o sistema executa automaticamente um modelo XGBoost treinado em dados históricos do Olist. O resultado indica a probabilidade e o nível de risco (**baixo**, **médio** ou **alto**) de a entrega atrasar, com base em peso, valor, frete, rota, distância e previsão de chuva no destino.

### Rastreio público
Qualquer pessoa com o código de rastreio (ex.: `TRK-A1B2C3D4`) pode consultar a situação atual da entrega e o histórico de checkpoints — sem precisar de conta na plataforma.

### Checkpoints em galpões
A empresa registra cada vez que um pacote passa por um galpão logístico. O histórico de checkpoints fica visível tanto para a empresa quanto para o cliente final pelo rastreio.

### Reavaliação periódica de risco
A cada 30 minutos, o sistema reavalia o risco de todas as entregas pendentes:
- Se o prazo já expirou, a entrega é marcada como **atrasada** e o sistema estima uma nova data de entrega (+3 dias úteis).
- Se o prazo ainda está no futuro, o risco é recalculado com dados de chuva atualizados. Caso o nível de risco mude, uma nova previsão é registrada automaticamente.

### Retreino automático do modelo
Após cada finalização de entrega (status → entregue), o sistema verifica se há amostras reais suficientes para retreinar o modelo. Quando o mínimo configurado é atingido, um novo ciclo de treinamento acontece em background, sem interromper o serviço.

---

## Fluxos principais

### 1. Cadastrar e acompanhar uma entrega

```
Empresa faz login
  → POST /auth/login          (obtém token JWT)

Empresa cadastra entrega
  → POST /entregas             (sistema calcula rota, consulta chuva, gera previsão)
  ← Retorna entrega com código de rastreio e nível de risco

[Pacote chega a um galpão]
  → POST /entregas/{id}/checkpoints   (registra passagem pelo galpão)

[Entrega concluída]
  → PATCH /entregas/{id}/finalizar    (marca como entregue)
  ← Sistema agenda retreino em background
```

### 2. Rastrear um pacote (cliente final)

```
Cliente recebe o código de rastreio do lojista (ex.: TRK-A1B2C3D4)

Consulta pública sem login
  → GET /rastreio/TRK-A1B2C3D4
  ← Retorna status, última previsão de risco e histórico de checkpoints
```

### 3. Retreino automático do modelo

```
Entrega finalizada
  → sistema conta novas amostras desde o último retreino
  → se >= RETREINO_MIN_AMOSTRAS:
      exporta entregas reais para entregas_historico
      treina novo modelo XGBoost
      substitui modelo em memória sem reiniciar o servidor
      registra métricas (ROC-AUC, PR-AUC) na tabela retreinos

Admin acompanha
  → GET /retreinos/status     (modelo ativo, métricas, amostras disponíveis)
  → GET /retreinos            (histórico de retreinos)
```

### 4. Reavaliação periódica de risco

```
A cada 30 minutos (APScheduler):
  → busca entregas com status='pendente'
  → para cada entrega:
      se prazo expirou  → status='atrasada', data_prevista_revisada = agora + 3 dias úteis
      caso contrário    → recalcula risco com nova consulta de chuva
                          salva nova previsão se o nível de risco mudou
```

---

## Status possíveis de uma entrega

| Status | Significado |
|---|---|
| `pendente` | Em trânsito, dentro do prazo |
| `entregue` | Entregue com sucesso |
| `atrasada` | Prazo expirado; nova data estimada pelo sistema |
| `cancelado` | Cancelada manualmente |
