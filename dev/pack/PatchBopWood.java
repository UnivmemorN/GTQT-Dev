import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.*;
import java.util.zip.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;

/** Translate the 1.8-era (count, meta) BOP wood lookups to October GT's (meta, count). */
class PatchBopWood {
    static final String SOURCE_HASH = "f8521a873e5316aaa7d400ab84d532f62cf59d35fb3c0de3af76572a19d66baa";
    static final String OWNER = "gregtechfoodoption/integration/bop/BiomesOPlentyWoodRecipe";
    static final String MODS = "gregtech/api/util/Mods";
    static final List<String> WOODS = List.of("sacred_oak","cherry","umbran","fir","ethereal","magic","mangrove","palm",
            "redwood","willow","pine","hellbark","jacaranda","mahogany","ebony","eucalyptus");

    static void check(boolean ok, String detail) {
        if (!ok) throw new IllegalArgumentException(detail);
    }

    static AbstractInsnNode adjacent(AbstractInsnNode node, boolean forward) {
        do { node = forward ? node.getNext() : node.getPrevious(); }
        while (node != null && node.getOpcode() < 0);
        return node;
    }

    static int integer(AbstractInsnNode n) {
        if (n.getOpcode() >= Opcodes.ICONST_0 && n.getOpcode() <= Opcodes.ICONST_5) return n.getOpcode() - Opcodes.ICONST_0;
        if (n instanceof IntInsnNode i && i.getOpcode() == Opcodes.BIPUSH) return i.operand;
        throw new IllegalArgumentException("Expected a constant wood metadata");
    }

    static byte[] patch(byte[] before) {
        ClassReader reader = new ClassReader(before);
        ClassNode tree = new ClassNode();
        reader.accept(tree, 0);
        check(tree.name.equals(OWNER), "Unexpected integration class");
        int total = 0;
        for (MethodNode method : tree.methods) {
            boolean init = method.name.equals("init") && method.desc.equals("()V");
            boolean defaults = method.name.equals("getDefaultEntries") && method.desc.equals("()Ljava/util/List;");
            if (!init && !defaults) continue;
            int index = 0;
            for (AbstractInsnNode node : method.instructions.toArray()) {
                if (!(node instanceof MethodInsnNode call) || !call.owner.equals(MODS) || !call.name.equals("getItem")) continue;
                check(call.getOpcode() == Opcodes.INVOKEVIRTUAL, "Expected Mods.getItem invocation");
                int component = index % 8, wood = index / 8;
                String species = init ? "dead" : WOODS.get(wood);
                String name = init ? "log_4" : switch(component) {
                    case 0 -> "log_" + wood / 4;
                    case 1 -> "planks_0";
                    case 2 -> "wood_slab_" + wood / 8;
                    case 3 -> species + "_stairs";
                    case 4 -> species + "_fence_gate";
                    case 5 -> species.equals("fir") ? "fir" : species + "_fence";
                    case 6 -> species + "_door";
                    default -> "boat_" + species;
                };
                boolean hasMeta = init || component < 3;
                check(call.desc.equals("(Ljava/lang/String;" + (hasMeta ? "II" : "I") + ")Lnet/minecraft/item/ItemStack;"), name);
                AbstractInsnNode last = adjacent(call, false);
                AbstractInsnNode amount = hasMeta ? adjacent(last, false) : last;
                AbstractInsnNode id = adjacent(amount, false);
                check(amount.getOpcode() == Opcodes.ICONST_1 && id instanceof LdcInsnNode &&
                        name.equals(((LdcInsnNode) id).cst), "Unexpected original lookup for " + name);
                check(adjacent(id, false) instanceof FieldInsnNode field && field.getOpcode() == Opcodes.GETSTATIC &&
                        field.owner.equals(MODS) && field.name.equals("BiomesOPlenty"), name);
                if (hasMeta) {
                    int meta = init ? 5 : component == 0 ? 4 + wood % 4 : component == 1 ? wood : wood % 8;
                    check(integer(last) == meta, "Unexpected original metadata for " + name);
                    method.instructions.remove(amount);
                    method.instructions.insertBefore(call, amount);
                } else {
                    method.instructions.set(amount, new InsnNode(Opcodes.ICONST_0));
                }
                if (name.equals("fir")) {
                    AbstractInsnNode recipe = adjacent(call, true);
                    check(recipe instanceof LdcInsnNode && name.equals(((LdcInsnNode) recipe).cst) &&
                            adjacent(recipe, true) instanceof MethodInsnNode use && use.name.equals("fence"), "Expected fir fence recipe");
                    ((LdcInsnNode) id).cst = "fir_fence";
                    ((LdcInsnNode) recipe).cst = "fir_fence";
                }
                index++;
            }
            check(index == (init ? 1 : 128), "Unexpected lookup count for " + method.name + ": " + index);
            total += index;
        }
        check(total == 129, "Incomplete BOP wood patch");
        ClassWriter writer = new ClassWriter(reader, 0);
        tree.accept(writer);
        return writer.toByteArray();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("Expected original-gtfo.jar separate-output.jar");
        Path input = Path.of(args[0]).toRealPath(), output = Path.of(args[1]).toAbsolutePath().normalize();
        String digest = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(input)));
        check(digest.equals(SOURCE_HASH) && !input.equals(output) && !(Files.exists(output) && Files.isSameFile(input, output)),
                "Expected the locked GTFO runtime and separate output path");
        Files.createDirectories(output.getParent());
        Path temp = Files.createTempFile(output.getParent(), "bop-wood-", ".jar");
        try {
            try (ZipFile source = new ZipFile(input.toFile()); ZipOutputStream out = new ZipOutputStream(Files.newOutputStream(temp))) {
                String member = OWNER + ".class";
                check(source.getEntry(member) != null, "Missing BOP integration class");
                for (ZipEntry e : Collections.list(source.entries())) {
                    ZipEntry copy = new ZipEntry(e.getName());
                    copy.setTimeLocal(LocalDateTime.of(2000, 1, 1, 0, 0));
                    out.putNextEntry(copy);
                    try (InputStream in = source.getInputStream(e)) {
                        if (member.equals(e.getName())) out.write(patch(in.readAllBytes()));
                        else in.transferTo(out);
                    }
                    out.closeEntry();
                }
            }
            Files.move(temp, output, StandardCopyOption.REPLACE_EXISTING);
        } finally { Files.deleteIfExists(temp); }
        System.out.println(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(output))) + "  " + output);
    }
}
