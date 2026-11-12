import java.nio.file.Files;
import java.nio.file.Path;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Label;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

/** Registration and production-name adaptations for the frozen July Core. */
public final class PatchJulyCore extends ClassVisitor implements Opcodes {
    private static final String PROXY = "meowmel/gtqtcore/common/CommonProxy";
    private static final String COIL = "meowmel/gtqtcore/common/blocks/BlockWireCoil$Builder$1";
    private static final String ITEMS = "meowmel/gtqtcore/common/items/GTQTMetaItems";
    private static final String GUARD = "registerClientDataRenderers";
    private int replaced;

    private PatchJulyCore(ClassWriter writer) {
        super(ASM9, writer);
    }

    @Override
    public MethodVisitor visitMethod(int access, String name, String desc, String signature, String[] exceptions) {
        MethodVisitor method = super.visitMethod(access, name, desc, signature, exceptions);
        if (!name.equals("registerItems") || !desc.equals("(Lnet/minecraftforge/event/RegistryEvent$Register;)V")) {
            return method;
        }
        return new MethodVisitor(ASM9, method) {
            @Override
            public void visitMethodInsn(int opcode, String owner, String name, String desc, boolean isInterface) {
                if (opcode == INVOKESTATIC && owner.equals(ITEMS) && name.equals("extraBehavior") && desc.equals("()V")) {
                    super.visitMethodInsn(INVOKESTATIC, PROXY, GUARD, "()V", false);
                    replaced++;
                } else {
                    super.visitMethodInsn(opcode, owner, name, desc, isInterface);
                }
            }
        };
    }

    @Override
    public void visitEnd() {
        if (replaced != 1) {
            throw new IllegalStateException("Expected one July renderer registration, found " + replaced);
        }
        // Keep the event handler's frames and the upstream client routine unchanged.
        MethodVisitor guard = super.visitMethod(ACC_PRIVATE | ACC_STATIC, GUARD, "()V", null, null);
        String fml = "net/minecraftforge/fml/common/FMLCommonHandler";
        String side = "net/minecraftforge/fml/relauncher/Side";
        Label done = new Label();
        guard.visitCode();
        guard.visitMethodInsn(INVOKESTATIC, fml, "instance", "()L" + fml + ";", false);
        guard.visitMethodInsn(INVOKEVIRTUAL, fml, "getSide", "()L" + side + ";", false);
        guard.visitMethodInsn(INVOKEVIRTUAL, side, "isClient", "()Z", false);
        guard.visitJumpInsn(IFEQ, done);
        guard.visitMethodInsn(INVOKESTATIC, ITEMS, "extraBehavior", "()V", false);
        guard.visitLabel(done);
        guard.visitFrame(F_SAME, 0, null, 0, null);
        guard.visitInsn(RETURN);
        guard.visitMaxs(1, 0);
        guard.visitEnd();
        super.visitEnd();
    }

    private static ClassVisitor coilNameAdapter(ClassWriter writer) {
        return new ClassVisitor(ASM9, writer) {
            boolean foundSrgName;

            @Override
            public MethodVisitor visitMethod(int access, String name, String desc, String signature, String[] exceptions) {
                if (desc.equals("()Ljava/lang/String;")) {
                    if (name.equals("getName")) throw new IllegalStateException("Unexpected existing coil name bridge");
                    if (name.equals("func_176610_l")) foundSrgName = true;
                }
                return super.visitMethod(access, name, desc, signature, exceptions);
            }

            @Override
            public void visitEnd() {
                if (!foundSrgName) throw new IllegalStateException("Expected the July coil's SRG name implementation");
                // GT's named interface and Minecraft's IStringSerializable share this implementation.
                MethodVisitor method = super.visitMethod(ACC_PUBLIC | ACC_BRIDGE | ACC_SYNTHETIC,
                        "getName", "()Ljava/lang/String;", null, null);
                method.visitCode();
                method.visitVarInsn(ALOAD, 0);
                method.visitMethodInsn(INVOKEVIRTUAL, COIL, "func_176610_l", "()Ljava/lang/String;", false);
                method.visitInsn(ARETURN);
                method.visitMaxs(1, 1);
                method.visitEnd();
                super.visitEnd();
            }
        };
    }

    public static void main(String[] args) throws Exception {
        ClassReader reader = new ClassReader(Files.readAllBytes(Path.of(args[0])));
        ClassWriter writer = new ClassWriter(reader, 0);
        ClassVisitor patch = switch (reader.getClassName()) {
            case PROXY -> new PatchJulyCore(writer);
            case COIL -> coilNameAdapter(writer);
            default -> throw new IllegalArgumentException("Unexpected class " + reader.getClassName());
        };
        reader.accept(patch, 0);
        Files.write(Path.of(args[1]), writer.toByteArray());
    }
}
