package format_2025

import (
	"fmt"
	"log/slog"
	"path/filepath"
	"strings"
)

// buildSlotPaths maps each slot index to the path its content occupies in the
// finished workenv.
//
// The command needs where a slot ends up, which is not what extraction reports.
// Extraction unpacks into a temporary directory and moves the result into
// place, so its paths name a directory that is gone by the time the command
// runs; and the cached path assigned every slot the workenv root, which is a
// directory rather than a file. Neither resolves {slot:N} to anything usable,
// so it is derived from the target instead, the way the Rust launcher and the
// Python executor both derive it.
//
// A slot whose target escapes the workenv is left out. The reference then stays
// unresolved and the caller refuses the command, which is the safe direction.
func buildSlotPaths(metadata *Metadata, workenvDir string, logger *slog.Logger) map[int]string {
	slotPaths := make(map[int]string, len(metadata.Slots))

	for _, slot := range metadata.Slots {
		target := strings.TrimSpace(slot.Target)
		target = strings.TrimPrefix(target, "{workenv}/")
		target = strings.TrimPrefix(target, "{workenv}")

		switch {
		case strings.Contains(slot.Operations, "tar"):
			// A tar slot spreads its entries across the workenv and has no single
			// path of its own, so it resolves to the workenv. Python's executor
			// settled on the same answer.
			slotPaths[slot.Slot] = filepath.Clean(workenvDir)

		case target == "" || target == ".":
			// Extraction gives a slot with no target a directory of its own.
			slotPaths[slot.Slot] = filepath.Join(workenvDir, fmt.Sprintf("slot_%d_%s", slot.Slot, slot.ID))

		default:
			resolved, err := resolveWorkenvTarget(workenvDir, target)
			if err != nil {
				logger.Warn("⚠️ Slot target does not resolve inside the workenv",
					"slot", slot.Slot, "id", slot.ID, "target", slot.Target, "error", err)
				continue
			}
			slotPaths[slot.Slot] = filepath.Clean(resolved)
		}
	}

	return slotPaths
}
