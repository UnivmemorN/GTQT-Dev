package gtqtdev.packclient;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.List;
import java.lang.reflect.Method;

import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.Loader;
import net.minecraftforge.fml.common.event.FMLInitializationEvent;
import net.minecraftforge.fml.common.event.FMLLoadCompleteEvent;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.common.gameevent.TickEvent;

/** Observes the client after the Forge handshake and one of the remote world's chunks have arrived. */
@Mod(modid = "gtqtpackclientprobe", version = "1", clientSideOnly = true, acceptableRemoteVersions = "*")
public final class ClientProbe {
    private final String user = "Pack19Probe";
    private boolean finished;
    private boolean returningToMenu;
    private int menuTicks;

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        MinecraftForge.EVENT_BUS.register(this);
    }

    @Mod.EventHandler
    public void verifyWoodEntries(FMLLoadCompleteEvent event) throws Exception {
        if (!Loader.isModLoaded("biomesoplenty") || !Loader.isModLoaded("gregtechfoodoption")) return;
        Method getter = Class.forName("gregtechfoodoption.integration.bop.BiomesOPlentyWoodRecipe")
                .getDeclaredMethod("getDefaultEntries");
        getter.setAccessible(true);
        List<?> entries = (List<?>) getter.invoke(null);
        String[] species = {"sacred_oak", "cherry", "umbran", "fir", "ethereal", "magic", "mangrove", "palm",
                "redwood", "willow", "pine", "hellbark", "jacaranda", "mahogany", "ebony", "eucalyptus"};
        String[] fields = {"log", "planks", "slab", "stairs", "fenceGate", "fence", "door", "boat"};
        if (entries.size() != species.length) throw new IllegalStateException("Incomplete GTFO BOP species registry");
        for (int i = 0; i < species.length; i++) {
            Object entry = entries.get(i);
            String wood = species[i];
            if (!wood.equals(entry.getClass().getField("woodName").get(entry))) throw new IllegalStateException(wood);
            String[] ids = {"log_" + i / 4, "planks_0", "wood_slab_" + i / 8, wood + "_stairs",
                    wood + "_fence_gate", wood + "_fence", wood + "_door", "boat_" + wood};
            int[] metadata = {4 + i % 4, i, i % 8, 0, 0, 0, 0, 0};
            for (int j = 0; j < fields.length; j++) {
                Object stack = entry.getClass().getField(fields[j]).get(entry);
                Object item = stack.getClass().getMethod("func_77973_b").invoke(stack);
                Object name = item.getClass().getMethod("getRegistryName").invoke(item);
                if (!("biomesoplenty:" + ids[j]).equals(String.valueOf(name)) ||
                        (int) stack.getClass().getMethod("func_77960_j").invoke(stack) != metadata[j] ||
                        (int) stack.getClass().getMethod("func_190916_E").invoke(stack) != 1)
                    throw new IllegalStateException("Bad GTFO BOP stack " + wood + " " + fields[j] + ": " + stack);
            }
        }
        System.out.println("GTQT_BOP_WOOD_OK species=16 registeredStacks=128");
    }

    @SubscribeEvent
    public void clientTick(TickEvent.ClientTickEvent event) throws Exception {
        if (finished || event.phase != TickEvent.Phase.END) return;
        // Production Forge remaps these Minecraft classes to stable SRG member names.
        Class<?> minecraft = Class.forName("net.minecraft.client.Minecraft");
        Object mc = minecraft.getMethod("func_71410_x").invoke(null);
        Object gui = minecraft.getField("field_71462_r").get(mc);
        if (returningToMenu) {
            if (minecraft.getField("field_71441_e").get(mc) == null &&
                    Class.forName("net.minecraft.client.gui.GuiMainMenu").isInstance(gui) && ++menuTicks >= 5) {
                finished = true;
                System.out.println("GTQT_PACK_CLIENT_EXIT_OK unloadedWorld=true menuTicks=" + menuTicks);
                minecraft.getMethod("func_71400_g").invoke(mc);
            }
            return;
        }
        if (gui != null && gui.getClass().getName().equals("net.minecraft.client.gui.GuiDisconnected")) {
            finished = true;
            String reason = "disconnected before receiving terrain";
            for (java.lang.reflect.Field field : gui.getClass().getDeclaredFields()) {
                if (!field.getType().getName().equals("net.minecraft.util.text.ITextComponent")) continue;
                field.setAccessible(true);
                Object message = field.get(gui);
                if (message != null) reason = String.valueOf(field.getType().getMethod("func_150260_c").invoke(message));
            }
            System.out.println("GTQT_PACK_CLIENT_FAILED reason=" + reason);
            minecraft.getMethod("func_71400_g").invoke(mc);
            return;
        }
        Object world = minecraft.getField("field_71441_e").get(mc);
        Object player = minecraft.getField("field_71439_g").get(mc);
        if (world == null || player == null || player.getClass().getField("field_70173_aa").getInt(player) < 20) return;
        Object handler = minecraft.getMethod("func_147114_u").invoke(mc);
        Object network = handler.getClass().getMethod("func_147298_b").invoke(handler);
        InetSocketAddress peer = (InetSocketAddress) network.getClass().getMethod("func_74430_c").invoke(network);
        if (!peer.getAddress().isLoopbackAddress() || peer.getPort() != Integer.getInteger("gtqt.probe.port")
                || (boolean) network.getClass().getMethod("func_150731_c").invoke(network)) {
            throw new IllegalStateException("Unexpected client transport or peer: " + peer);
        }
        int x = (int) Math.floor(player.getClass().getField("field_70165_t").getDouble(player)) >> 4;
        int z = (int) Math.floor(player.getClass().getField("field_70161_v").getDouble(player)) >> 4;
        Object provider = world.getClass().getMethod("func_72863_F").invoke(world);
        if (provider.getClass().getMethod("func_186026_b", int.class, int.class).invoke(provider, x, z) == null) return;
        UUID id = (UUID) player.getClass().getMethod("func_110124_au").invoke(player);
        if (!user.equals(player.getClass().getMethod("func_70005_c_").invoke(player))
                || !id.equals(UUID.nameUUIDFromBytes(("OfflinePlayer:" + user).getBytes(StandardCharsets.UTF_8)))) {
            throw new IllegalStateException("Unexpected server player identity " + id);
        }
        returningToMenu = true;
        System.out.println("GTQT_PACK_CLIENT_OK phase=" + System.getProperty("gtqt.probe.phase") + " user=" + user
                + " uuid=" + id + " port=" + peer.getPort() + " dimension="
                + player.getClass().getField("field_71093_bK").getInt(player) + " chunk=" + x + "," + z);
        // Match the multiplayer Disconnect button, then allow client and mod teardown ticks.
        world.getClass().getMethod("func_72882_A").invoke(world);
        minecraft.getMethod("func_71403_a", Class.forName("net.minecraft.client.multiplayer.WorldClient"))
                .invoke(mc, (Object) null);
        Class<?> screen = Class.forName("net.minecraft.client.gui.GuiScreen");
        Object menu = Class.forName("net.minecraft.client.gui.GuiMainMenu").getConstructor().newInstance();
        minecraft.getMethod("func_147108_a", screen).invoke(mc, menu);
    }
}
