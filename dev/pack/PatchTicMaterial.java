import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.*;
import java.util.zip.*;
import org.objectweb.asm.*;

/** Run with the prepared JDK 17 and Gradle 8.5's ASM 9.5 on the class path. */
class PatchTicMaterial {
    static final String INPUT = "6ee0c0fc7756b8c8c1a4693d2943c711faefcb36af2db8170d548573e0d77671";
    static final String OWNER = "gregtech/integration/tconstruct/materials/ToolMaterialRegistrar";
    static final String TC = "slimeknights/tconstruct/library/";
    static final String MATERIAL = TC + "materials/Material";
    static final String STATS = TC + "materials/IMaterialStats";
    static final String MERGE = "(L" + MATERIAL + ";Lgregtech/api/unification/material/Material;)V";
    static final List<String> TYPES = List.of("head", "handle", "extra", "bow", "shaft");
    static final String WOOD = "gregtech/loaders/recipe/WoodRecipeLoader";
    static final String ENTRY = "gregtech/loaders/recipe/WoodTypeEntry";
    static final String STACK = "net/minecraft/item/ItemStack";

    static byte[] patch(byte[] data) {
        ClassReader source = new ClassReader(data);
        if (!OWNER.equals(source.getClassName())) throw new IllegalArgumentException("Unexpected registrar");
        ClassWriter out = new ClassWriter(source, 0);
        List<String> changed = new ArrayList<>();
        source.accept(new ClassVisitor(Opcodes.ASM9, out) {
            @Override public MethodVisitor visitMethod(int access, String name, String desc, String signature, String[] exceptions) {
                MethodVisitor dst = super.visitMethod(access, name, desc, signature, exceptions);
                if (!name.equals("mergeMaterial") || !desc.equals(MERGE)) return dst;
                return new MethodVisitor(Opcodes.ASM9, dst) {
                    String stat;
                    Label missing;
                    boolean merged, inMissingBranch;
                    @Override public void visitLdcInsn(Object value) {
                        if (TYPES.contains(value)) {
                            if (stat != null) throw new IllegalStateException("Unfinished material branch " + stat);
                            stat = (String) value;
                        }
                        super.visitLdcInsn(value);
                    }
                    @Override public void visitJumpInsn(int op, Label destination) {
                        if (stat != null && op == Opcodes.IFNULL) {
                            if (missing != null) throw new IllegalStateException("Multiple null checks for " + stat);
                            missing = destination;
                        }
                        super.visitJumpInsn(op, destination);
                    }
                    @Override public void visitLabel(Label label) {
                        if (label == missing) {
                            if (!merged) throw new IllegalStateException("Missing update in existing-stat branch");
                            inMissingBranch = true;
                        }
                        super.visitLabel(label);
                    }
                    @Override public void visitMethodInsn(int op, String owner, String called, String descriptor, boolean itf) {
                        if (owner.equals(TC + "TinkerRegistry") && called.equals("addMaterialStats")) {
                            if (stat == null || missing == null || op != Opcodes.INVOKESTATIC ||
                                    !descriptor.equals("(L" + MATERIAL + ";L" + STATS + ";)V")) {
                                throw new IllegalStateException("Unexpected material registration");
                            }
                            if (!inMissingBranch) {
                                if (merged) throw new IllegalStateException("Multiple updates for " + stat);
                                super.visitMethodInsn(Opcodes.INVOKEVIRTUAL, MATERIAL, "addStats", "(L" + STATS + ";)L" + MATERIAL + ";", false);
                                super.visitInsn(Opcodes.POP);
                                merged = true;
                                return;
                            }
                            changed.add(stat);
                            stat = null;
                            missing = null;
                            merged = false;
                            inMissingBranch = false;
                        }
                        super.visitMethodInsn(op, owner, called, descriptor, itf);
                    }
                };
            }
        }, 0);
        if (!changed.equals(TYPES)) throw new IllegalStateException("Expected existing and missing branches for " + TYPES + ", got " + changed);
        return out.toByteArray();
    }

    static byte[] stableWoodRecipeIds(byte[] data) {
        ClassReader source = new ClassReader(data);
        ClassWriter out = new ClassWriter(source, ClassWriter.COMPUTE_MAXS);
        int[] count = {0};
        source.accept(new ClassVisitor(Opcodes.ASM9, out) {
            @Override public MethodVisitor visitMethod(int access, String name, String desc, String sig, String[] ex) {
                MethodVisitor dst = super.visitMethod(access, name, desc, sig, ex);
                if (!name.equals("registerWoodTypeRecipe") || !desc.equals("(ZL" + ENTRY + ";)V")) return dst;
                return new MethodVisitor(Opcodes.ASM9, dst) {
                    @Override public void visitMethodInsn(int op, String owner, String name, String descriptor, boolean itf) {
                        if (op == Opcodes.INVOKESTATIC && owner.equals("gregtech/api/util/GTUtility") &&
                                name.equals("generateRandomString") && descriptor.equals("(I)Ljava/lang/String;")) {
                            // Replace the random prefix with the plank's registry namespace/path and metadata.
                            // Fireproof and ordinary planks can share the Forestry species name.
                            super.visitInsn(Opcodes.POP);
                            super.visitVarInsn(Opcodes.ALOAD, 1);
                            super.visitFieldInsn(Opcodes.GETFIELD, ENTRY, "planks", "L" + STACK + ";");
                            super.visitMethodInsn(Opcodes.INVOKEVIRTUAL, STACK, "serializeNBT", "()Lnet/minecraft/nbt/NBTTagCompound;", false);
                            super.visitLdcInsn("id");
                            super.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "net/minecraft/nbt/NBTTagCompound", "func_74779_i", "(Ljava/lang/String;)Ljava/lang/String;", false);
                            super.visitIntInsn(Opcodes.BIPUSH, ':');
                            super.visitIntInsn(Opcodes.BIPUSH, '/');
                            super.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/lang/String", "replace", "(CC)Ljava/lang/String;", false);
                            super.visitLdcInsn("/");
                            super.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/lang/String", "concat", "(Ljava/lang/String;)Ljava/lang/String;", false);
                            super.visitVarInsn(Opcodes.ALOAD, 1);
                            super.visitFieldInsn(Opcodes.GETFIELD, ENTRY, "planks", "L" + STACK + ";");
                            super.visitMethodInsn(Opcodes.INVOKEVIRTUAL, STACK, "func_77960_j", "()I", false);
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, "java/lang/Integer", "toString", "(I)Ljava/lang/String;", false);
                            super.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/lang/String", "concat", "(Ljava/lang/String;)Ljava/lang/String;", false);
                            count[0]++;
                        } else super.visitMethodInsn(op, owner, name, descriptor, itf);
                    }
                };
            }
        }, 0);
        if (count[0] != 1) throw new IllegalStateException("Expected exactly one random wood prefix");
        return out.toByteArray();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("Expected original-runtime.jar output.jar");
        Path input = Path.of(args[0]).toRealPath(), output = Path.of(args[1]).toAbsolutePath().normalize();
        String digest = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(input)));
        if (!digest.equals(INPUT) || input.equals(output) || (Files.exists(output) && Files.isSameFile(input, output)))
            throw new IllegalArgumentException("Expected the locked October SRG runtime and a separate output");
        Files.createDirectories(output.getParent());
        Path tmp = Files.createTempFile(output.getParent(), "gt-tic-", ".jar");
        try {
            try (ZipFile source = new ZipFile(input.toFile());
                 ZipOutputStream out = new ZipOutputStream(new BufferedOutputStream(Files.newOutputStream(tmp)))) {
                ZipEntry target = source.getEntry(OWNER + ".class");
                if (target == null) throw new IllegalStateException("No ToolMaterialRegistrar");
                byte[] patched;
                try (InputStream in = source.getInputStream(target)) { patched = patch(in.readAllBytes()); }
                byte[] wood;
                try (InputStream in = source.getInputStream(source.getEntry(WOOD + ".class"))) {
                    wood = stableWoodRecipeIds(in.readAllBytes());
                }
                for (ZipEntry entry : Collections.list(source.entries())) {
                    ZipEntry copy = new ZipEntry(entry.getName());
                    copy.setTimeLocal(LocalDateTime.of(2000, 1, 1, 0, 0));
                    out.putNextEntry(copy);
                    if (entry.getName().equals(target.getName())) out.write(patched);
                    else if (entry.getName().equals(WOOD + ".class")) out.write(wood);
                    else try (InputStream in = source.getInputStream(entry)) { in.transferTo(out); }
                    out.closeEntry();
                }
            }
            Files.move(tmp, output, StandardCopyOption.REPLACE_EXISTING);
        } finally {
            Files.deleteIfExists(tmp);
        }
        System.out.println(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(output))) + "  " + output);
    }
}
