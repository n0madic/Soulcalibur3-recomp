// Prints all references to the given addresses with the containing function.
// Args: <hex address> [<hex address> ...]
//@category SC3
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class Xrefs extends GhidraScript {
    @Override
    protected void run() throws Exception {
        for (String s : getScriptArgs()) {
            Address a = toAddr(Long.parseLong(s.replace("0x", ""), 16));
            println("== refs to " + a);
            for (Reference ref : getReferencesTo(a)) {
                Function f = getFunctionContaining(ref.getFromAddress());
                println("  " + ref.getFromAddress() + " " + ref.getReferenceType() + " in " + (f == null ? "?" : f.getEntryPoint().toString()));
            }
        }
    }
}
