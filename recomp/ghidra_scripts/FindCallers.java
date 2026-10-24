// Prints the callers of a function breadth-first up to a depth.
// Args: <hex address> <depth>
//@category SC3
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

import java.util.*;

public class FindCallers extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        Address start = toAddr(Long.parseLong(args[0].replace("0x", ""), 16));
        int depth = Integer.parseInt(args[1]);
        Function root = getFunctionContaining(start);
        if (root == null) { println("no function at " + start); return; }
        Set<Function> seen = new HashSet<>();
        List<Function> level = new ArrayList<>();
        level.add(root);
        seen.add(root);
        for (int d = 0; d <= depth && !level.isEmpty(); d++) {
            StringBuilder sb = new StringBuilder("depth " + d + ":");
            List<Function> next = new ArrayList<>();
            for (Function f : level) {
                sb.append(" ").append(f.getEntryPoint());
                for (Reference ref : getReferencesTo(f.getEntryPoint())) {
                    if (!ref.getReferenceType().isCall() && !ref.getReferenceType().isJump()) continue;
                    Function c = getFunctionContaining(ref.getFromAddress());
                    if (c != null && seen.add(c)) next.add(c);
                }
            }
            println(sb.toString());
            level = next;
        }
    }
}
