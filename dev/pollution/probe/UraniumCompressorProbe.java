package gtqtdev.probe;

import gregtech.api.GTValues;
import gregtech.api.capability.GregtechCapabilities;
import gregtech.api.capability.GregtechTileCapabilities;
import gregtech.api.capability.IEnergyContainer;
import gregtech.api.capability.impl.AbstractRecipeLogic;
import gregtech.api.metatileentity.MetaTileEntity;
import gregtech.api.metatileentity.SimpleMachineMetaTileEntity;
import gregtech.api.metatileentity.interfaces.IGregTechTileEntity;
import gregtech.api.recipes.RecipeMaps;
import gregtech.api.unification.OreDictUnifier;
import gregtech.api.unification.material.Materials;
import gregtech.api.unification.ore.OrePrefix;
import gregtech.common.metatileentities.MetaTileEntities;
import net.minecraft.block.Block;
import net.minecraft.block.state.IBlockState;
import net.minecraft.item.ItemStack;
import net.minecraft.util.EnumFacing;
import net.minecraft.util.ITickable;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;
import net.minecraft.world.WorldServer;
import net.minecraftforge.items.IItemHandler;

import java.lang.reflect.Method;

/** Feeds LV packets to a placed compressor and hands its extracted output to the infusion fixture. */
final class UraniumCompressorProbe {
    private static final long VOLTAGE = GTValues.V[GTValues.LV];
    private static final int PACKETS = 24;
    private static final int EU_PER_TICK = 2;
    private static final int WORK_TICKS = 300;
    private static final long COST = EU_PER_TICK * WORK_TICKS;

    private static void require(boolean ok, String reason) {
        if (!ok) throw new IllegalStateException("Uranium compressor: " + reason);
    }

    private static int count(ItemStack stack) throws ReflectiveOperationException {
        return (int) ItemStack.class.getMethod("func_190916_E").invoke(stack);
    }

    private static void insertDust(IItemHandler input, int amount) throws Exception {
        ItemStack dust = OreDictUnifier.get(OrePrefix.dust, Materials.Uranium235, amount);
        require(count(dust) == amount && count(input.insertItem(0, dust, false)) == 0,
                "failed to insert " + amount + " uranium-235 dust");
    }

    private static void sendPacket(IEnergyContainer energy) {
        require(energy.acceptEnergyFromNetwork(EnumFacing.UP, VOLTAGE, 1) == 1,
                "LV power input did not accept a packet");
    }

    private static SimpleMachineMetaTileEntity lvPrototype() {
        for (SimpleMachineMetaTileEntity candidate : MetaTileEntities.COMPRESSOR) {
            if (candidate != null && candidate.getTier() == GTValues.LV) return candidate;
        }
        throw new IllegalStateException("No registered LV compressor");
    }

    static ItemStack run(WorldServer world, String phase, String route) throws Exception {
        boolean reload = "reload".equals(phase);
        require(reload || "create".equals(phase), "unknown phase " + phase);
        require("altar".equals(route) || "industrial".equals(route), "unknown route " + route);
        BlockPos pos = "altar".equals(route) ? new BlockPos(48, 120, 16) : new BlockPos(0, 120, -40);
        SimpleMachineMetaTileEntity lv = lvPrototype();
        // Reading the state loads the persisted chunk before testing the full MTE identity.
        World.class.getMethod("func_180495_p", BlockPos.class).invoke(world, pos);
        Method getTile = World.class.getMethod("func_175625_s", BlockPos.class);
        if (!reload) {
            require(getTile.invoke(world, pos) == null, "occupied fixture position " + pos);
            IBlockState blockState = (IBlockState) Block.class.getMethod("func_176223_P").invoke(lv.getBlock());
            World.class.getMethod("func_180501_a", BlockPos.class, IBlockState.class, int.class)
                    .invoke(world, pos, blockState, 3);
        }
        IGregTechTileEntity holder = (IGregTechTileEntity) getTile.invoke(world, pos);
        require(holder != null, "missing GregTech tile at " + pos);
        MetaTileEntity machine = reload ? holder.getMetaTileEntity() : holder.setMetaTileEntity(lv);
        require(machine != null && lv.metaTileEntityId.equals(machine.metaTileEntityId), "incorrect compressor");
        AbstractRecipeLogic work = machine.getCapability(GregtechTileCapabilities.CAPABILITY_RECIPE_LOGIC, null);
        IEnergyContainer energy = machine.getCapability(GregtechCapabilities.CAPABILITY_ENERGY_CONTAINER, EnumFacing.UP);
        require(work != null && work.getRecipeMap() == RecipeMaps.COMPRESSOR_RECIPES, "wrong recipe map");
        require(energy != null && energy.getInputVoltage() == VOLTAGE, "wrong input voltage");
        IItemHandler input = machine.getImportItems();
        IItemHandler output = machine.getExportItems();
        require(count(input.getStackInSlot(0)) == 0 && count(output.getStackInSlot(0)) == 0 && work.getProgress() == 0,
                "expected empty, idle compressor after prior handoff");
        long storedBefore = energy.getEnergyStored();
        require(storedBefore == (reload ? VOLTAGE * PACKETS - COST : 0),
                "unexpected stored EU before " + phase + ": " + storedBefore);
        Method tick = ITickable.class.getMethod("func_73660_a");

        insertDust(input, 8);
        sendPacket(energy);
        for (int i = 0; i < 25; i++) tick.invoke(holder);
        require(count(input.getStackInSlot(0)) == 8 && count(output.getStackInSlot(0)) == 0
                        && work.getProgress() == 0 && energy.getEnergyStored() == storedBefore + VOLTAGE,
                "eight dust started work or consumed resources");

        insertDust(input, 1);
        long spent = 0;
        int paidTicks = 0;
        int ticks = 0;
        while (count(output.getStackInSlot(0)) == 0 && ticks < WORK_TICKS + 50) {
            if (ticks < PACKETS - 1) sendPacket(energy);
            long before = energy.getEnergyStored();
            tick.invoke(holder);
            long debit = before - energy.getEnergyStored();
            require(debit == 0 || debit == EU_PER_TICK, "unexpected per-tick energy debit " + debit);
            if (debit > 0) {
                paidTicks++;
                spent += debit;
            }
            ticks++;
        }
        long storedAfter = energy.getEnergyStored();
        require(paidTicks == WORK_TICKS && spent == COST && storedAfter == storedBefore + VOLTAGE * PACKETS - spent,
                "energy/time mismatch: paidTicks=" + paidTicks + ", spent=" + spent + ", stored=" + storedAfter);
        require(count(input.getStackInSlot(0)) == 0 && count(output.getStackInSlot(0)) == 1,
                "expected all nine dust consumed and exactly one item in the output");
        ItemStack block = output.extractItem(0, 1, false);
        require(count(block) == 1 && InfusionCases.isUranium235Block(block) && count(output.getStackInSlot(0)) == 0,
                "failed to extract a single blockUranium235 from the compressor");
        machine.markDirty();
        System.out.println("GTQT_COMPRESSOR_OK phase=" + phase + " route=" + route + " machine=" + machine.metaTileEntityId
                + " dust=9 blocks=1 ticks=" + paidTicks + " eut=" + EU_PER_TICK + " eu=" + spent
                + " supplied=" + (VOLTAGE * PACKETS) + " storedBefore=" + storedBefore + " storedAfter=" + storedAfter
                + " shortInputRejected=true");
        return block;
    }
}
