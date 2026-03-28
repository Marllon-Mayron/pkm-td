# core/profiler.py
import time
import pygame
from collections import defaultdict


class Profiler:
    """Sistema de profiling para identificar gargalos de performance"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.timings = defaultdict(list)
        self.max_samples = 60  # Mantém últimos 60 frames
        self.enabled = False
        self.frame_count = 0
        self._start_time = None
        self._current_section = None
        self._frame_start = None
        self._frame_timings = defaultdict(float)

    def start(self):
        """Ativa o profiling"""
        self.enabled = True
        self.timings.clear()
        self._frame_timings.clear()
        print("\n" + "=" * 60)
        print("[PROFILER] Profiling ATIVADO - Pressione F2 novamente para ver resultados")
        print("=" * 60 + "\n")

    def stop(self):
        """Desativa o profiling e mostra resultados"""
        self.enabled = False
        self.print_results()

    def begin_frame(self):
        """Inicia a medição de um frame"""
        if not self.enabled:
            return
        self._frame_start = time.perf_counter()

    def end_frame(self):
        """Finaliza a medição do frame"""
        if not self.enabled or self._frame_start is None:
            return
        elapsed = (time.perf_counter() - self._frame_start) * 1000
        self.timings["FRAME_TOTAL"].append(elapsed)
        self._frame_start = None

        # Mantém apenas os últimos N samples
        if len(self.timings["FRAME_TOTAL"]) > self.max_samples:
            self.timings["FRAME_TOTAL"].pop(0)

    def begin_section(self, name):
        """Inicia uma seção para medir tempo"""
        if not self.enabled:
            return
        self._current_section = name
        self._start_time = time.perf_counter()

    def end_section(self):
        """Finaliza a seção atual"""
        if not self.enabled or self._start_time is None:
            return

        elapsed = (time.perf_counter() - self._start_time) * 1000  # ms
        self.timings[self._current_section].append(elapsed)

        # Mantém apenas os últimos N samples
        if len(self.timings[self._current_section]) > self.max_samples:
            self.timings[self._current_section].pop(0)

        self._start_time = None
        self._current_section = None

    def print_results(self):
        """Exibe os resultados do profiling"""
        if not self.timings:
            print("\n[PROFILER] Nenhum dado coletado")
            return

        print("\n" + "=" * 70)
        print("PROFILING RESULTS (média dos últimos frames)")
        print("=" * 70)

        results = []
        for name, times in self.timings.items():
            if times:
                avg = sum(times) / len(times)
                max_t = max(times)
                min_t = min(times)
                results.append((name, avg, max_t, min_t, len(times)))

        # Ordena por média decrescente
        results.sort(key=lambda x: x[1], reverse=True)

        # Calcula total do frame
        frame_total = 0
        frame_avg = 0
        for name, avg, max_t, min_t, samples in results:
            if name == "FRAME_TOTAL":
                frame_avg = avg
                frame_total = avg
                break

        print(f"\n{'Seção':<40} {'Média(ms)':<12} {'Máx(ms)':<12} {'Mín(ms)':<12} {'% do Frame':<12}")
        print("-" * 88)

        for name, avg, max_t, min_t, samples in results:
            if name == "FRAME_TOTAL":
                continue
            percent = (avg / frame_total * 100) if frame_total > 0 else 0
            # Limita nome para 40 caracteres
            short_name = name[:40]
            print(f"{short_name:<40} {avg:>8.2f}ms  {max_t:>8.2f}ms  {min_t:>8.2f}ms  {percent:>8.1f}%")

        print("-" * 88)
        print(f"{'FRAME_TOTAL':<40} {frame_avg:>8.2f}ms")
        print(f"\nFPS médio: {1000 / frame_avg:.1f}" if frame_avg > 0 else "N/A")
        print("=" * 70 + "\n")


# Instância global
profiler = Profiler()