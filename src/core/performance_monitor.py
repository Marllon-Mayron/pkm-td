# src/core/performance_monitor.py
"""
Sistema de monitoramento de performance para debug
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional
import pygame


@dataclass
class PerformanceMetric:
    """Métrica de performance para uma seção"""
    total_time: float = 0.0
    call_count: int = 0
    min_time: float = float('inf')
    max_time: float = 0.0

    def add_measurement(self, duration_ms: float):
        self.total_time += duration_ms
        self.call_count += 1
        self.min_time = min(self.min_time, duration_ms)
        self.max_time = max(self.max_time, duration_ms)

    def get_average(self) -> float:
        return self.total_time / self.call_count if self.call_count > 0 else 0.0

    def reset(self):
        self.total_time = 0.0
        self.call_count = 0
        self.min_time = float('inf')
        self.max_time = 0.0


class PerformanceMonitor:
    """Monitor de performance para debug"""

    def __init__(self):
        self.metrics: Dict[str, PerformanceMetric] = defaultdict(PerformanceMetric)
        self.frame_count = 0
        self.last_print_time = 0
        self.current_section: Optional[str] = None
        self.section_start: float = 0
        self.total_frame_time: float = 0
        self.enabled = False
        self.print_interval = 60  # Print a cada 60 frames
        self._section_stack = []  # Para seções aninhadas

    def set_enabled(self, enabled: bool):
        """Habilita/desabilita o monitor"""
        self.enabled = enabled
        if not enabled:
            self.reset()

    def start_frame(self):
        """Inicia medição do frame"""
        if not self.enabled:
            return
        self.frame_count += 1
        self.total_frame_time = time.perf_counter()

    def end_frame(self):
        """Finaliza medição do frame"""
        if not self.enabled:
            return
        total_duration = (time.perf_counter() - self.total_frame_time) * 1000
        self.metrics["TOTAL_FRAME"].add_measurement(total_duration)

        # Print a cada N frames
        if self.frame_count % self.print_interval == 0:
            self.print_stats()

    def start_section(self, name: str):
        """Inicia medição de uma seção"""
        if not self.enabled:
            return
        self._section_stack.append((name, time.perf_counter()))

    def end_section(self):
        """Finaliza medição da seção atual"""
        if not self.enabled or not self._section_stack:
            return
        name, start_time = self._section_stack.pop()
        duration = (time.perf_counter() - start_time) * 1000
        self.metrics[name].add_measurement(duration)

    def reset(self):
        """Reseta todas as métricas"""
        for metric in self.metrics.values():
            metric.reset()
        self.frame_count = 0
        self._section_stack.clear()

    def print_stats(self):
        """Printa estatísticas de performance"""
        if not self.metrics:
            return

        print("\n" + "=" * 80)
        print(f"PERFORMANCE REPORT - Frame {self.frame_count}")
        print("=" * 80)

        # Ordena por tempo médio (maior primeiro)
        sorted_metrics = sorted(
            self.metrics.items(),
            key=lambda x: x[1].get_average(),
            reverse=True
        )

        total_frame_time = 0
        warnings = []

        for name, metric in sorted_metrics:
            avg = metric.get_average()
            if name == "TOTAL_FRAME":
                total_frame_time = avg

            # Calcula barra visual (50 caracteres)
            if total_frame_time > 0:
                bar_length = min(50, int(avg / total_frame_time * 50))
            else:
                bar_length = 0
            bar = "█" * bar_length + "░" * (50 - bar_length)

            # Formata a linha
            print(f"{name:35} | {bar} | {avg:6.2f}ms  "
                  f"(min:{metric.min_time:5.2f} max:{metric.max_time:5.2f} calls:{metric.call_count})")

            # Coleta warnings
            if name != "TOTAL_FRAME" and avg > 5.0:
                warnings.append(f"⚠️  {name} está lento ({avg:.2f}ms)")

        print("=" * 80)

        # Mostra warnings
        if warnings:
            print("\n⚠️  ALERTAS DE PERFORMANCE:")
            for warning in warnings:
                print(f"  {warning}")
            print()

        # Sugestões baseadas nos dados
        self._print_suggestions(sorted_metrics, total_frame_time)

        print("=" * 80 + "\n")

    def _print_suggestions(self, sorted_metrics, total_frame_time):
        """Printa sugestões de otimização"""
        if total_frame_time > 16.67:  # Mais que 60 FPS
            print(f"\n💡 SUGESTÕES (Frame time: {total_frame_time:.2f}ms > 16.67ms):")

            for name, metric in sorted_metrics[:3]:
                avg = metric.get_average()
                percentage = (avg / total_frame_time) * 100
                if percentage > 10:
                    print(f"  • {name} consome {percentage:.1f}% do tempo ({avg:.2f}ms)")

                    # Sugestões específicas
                    if "RENDER_MAP" in name:
                        print(f"    → Considere reduzir o tamanho do mapa ou usar tiles menores")
                    elif "RENDER_ENEMIES" in name:
                        print(f"    → Reduza o número de inimigos simultâneos")
                    elif "WAVE_MANAGER" in name:
                        print(f"    → Aumente o intervalo de spawn ou reduza a velocidade")
                    elif "POKEMON_UPDATES" in name:
                        print(f"    → Limite o número de Pokémon no campo")


# Instância global
perf_monitor = PerformanceMonitor()