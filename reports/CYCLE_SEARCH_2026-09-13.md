# Busca integral de ciclos em números com mais de um milhão de dígitos — 2026-09-13

## Objetivo e método

Foram avaliadas até o fim as sequências de Collatz de dois inteiros positivos
distintos, cada um com exatamente **1.000.001 dígitos decimais**. Não foi usado
limite de passos: cada avaliação só terminou ao chegar a `1` ou retornar
exatamente ao seu próprio valor inicial.

Os candidatos foram gerados deterministicamente pelo projeto com a estratégia
`S6-residue-class-top10`, semente `e005-million-digit-full-20260913` e módulo
`2^128 + 1`. As classes de resíduo foram validadas antes da avaliação.

Para tornar a execução integral viável, foi usado o avaliador GMP em
`tools/collatz_gmp.c`. Ele aplica `3n + 1` e agrupa somente as divisões por dois
consecutivas, mas soma individualmente todas elas ao comprimento não acelerado.
Esse agrupamento não altera a sequência ou seus resultados. O máximo só pode
ocorrer no início ou imediatamente depois de um passo ímpar; por isso também é
retido exatamente. A detecção de retorno considera o inteiro inicial em todas as
posições representadas pelo bloco de divisões.

## Resultados completos

| Sequência | Início (abreviado) | Dígitos | Comprimento total | Ímpares | Pares | Dígitos do máximo | Desfecho | Ciclo não trivial |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `2135854184534919…2131212028906769` | 1.000.001 | 23.977.946 | 7.990.838 | 15.987.108 | 1.000.001 | chegou a 1 | não |
| 2 | `3606252225613928…7950959570674163` | 1.000.001 | 24.017.980 | 8.006.325 | 16.011.655 | 1.000.003 | chegou a 1 | não |

### Sumário agregado

- **Sequências integralmente avaliadas:** 2.
- **Passos exatos executados:** 47.995.926.
- **Comprimento mínimo:** 23.977.946.
- **Comprimento máximo:** 24.017.980.
- **Comprimento médio e mediano:** 23.997.963.
- **Passos ímpares:** 15.997.163 no total (aproximadamente 33,33%).
- **Passos pares:** 31.998.763 no total (aproximadamente 66,67%).
- **Sequências que chegaram a 1:** 2.
- **Retornos ao inteiro inicial:** 0.
- **Ciclos não triviais encontrados:** 0.
- **Tempo de avaliação por sequência:** 497 e 502 segundos. As duas avaliações
  foram executadas parcialmente em paralelo, portanto esses tempos não devem ser
  somados para inferir o tempo de parede do ensaio.

## Integridade e artefatos

O arquivo `results/e005-s6-million-digit-full-2/summary.json` preserva os dois
inteiros iniciais e os máximos completos, além de todos os contadores acima. Os
SHA-256 dos textos decimais canônicos dos inícios são, respectivamente:

1. `a3b8053cfa1f6d1631ad2889b2ac51aab8fa1e8b412afd46fc42e1f729a8215b`;
2. `9f35ace4849f3ece27f0c49d82763a8ab3cc0b0b62d5247d9b6a89ed31557e44`.

## Conclusão e alcance

Os dois números testados chegaram a `1`; portanto, suas sequências completas não
contêm ciclo não trivial. A segunda sequência fez uma excursão até um número de
1.000.003 dígitos antes de descer.

O resultado se limita rigorosamente a esses dois candidatos determinísticos. Ele
não exclui ciclos para outros inteiros e não constitui prova da conjectura de
Collatz.
