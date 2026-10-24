// Decompiles the functions containing the given addresses and writes C-like text to a file.
// Args: <output file> <hex address> [<hex address> ...]
//@category SC3
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

import java.io.PrintWriter;

public class DumpDecomp extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            printerr("usage: DumpDecomp <out> <addr>...");
            return;
        }
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        try (PrintWriter out = new PrintWriter(args[0])) {
            for (int i = 1; i < args.length; i++) {
                Address a = toAddr(Long.parseLong(args[i].replace("0x", ""), 16));
                Function f = getFunctionContaining(a);
                if (f == null) {
                    out.println("// ===== " + args[i] + ": no function");
                    continue;
                }
                out.println("// ===== " + f.getName() + " @ " + f.getEntryPoint() + " (requested " + args[i] + ")");
                DecompileResults r = ifc.decompileFunction(f, 120, monitor);
                if (r.decompileCompleted()) {
                    out.println(r.getDecompiledFunction().getC());
                } else {
                    out.println("// decompile failed: " + r.getErrorMessage());
                }
            }
        }
    }
}
