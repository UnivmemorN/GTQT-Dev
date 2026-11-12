package gtqtdev.probe;

import gregtech.api.capability.IEnergyContainer;
import gregtech.api.capability.impl.MultiblockRecipeLogic;
import gregtech.api.metatileentity.multiblock.RecipeMapMultiblockController;
import gregtech.api.recipes.logic.CrossRecipeParallelScheduler;
import gregtech.api.recipes.logic.RecipeSlot;
import gregtech.api.unification.material.Material;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTBase;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.util.ResourceLocation;
import net.minecraftforge.fluids.IFluidTank;
import net.minecraftforge.fml.common.registry.ForgeRegistries;
import net.minecraftforge.items.IItemHandlerModifiable;

import java.util.Collections;
import java.util.List;

/** An already paid snapshot from the October GT slot format, loaded in a formed production controller. */
final class LegacyInfusionProbe {
    static void exercise(RecipeMapMultiblockController machine, IFluidTank magic, Material fuel, String phase)
            throws Exception {
        MultiblockRecipeLogic work = machine.getRecipeMapWorkable();
        IEnergyContainer energy = machine.getEnergyContainer();
        IItemHandlerModifiable output = machine.getOutputInventory();
        Item cobble = ForgeRegistries.ITEMS.getValue(new ResourceLocation("minecraft:cobblestone"));
        List<InfusionCases.Batch> batches = InfusionCases.batches();
        require(!machine.canVoidRecipeItemOutputs(), "item voiding unexpectedly enabled");
        if ("create".equals(phase)) {
            for (int i = 0; i < output.getSlots(); i++) output.setStackInSlot(i, new ItemStack(cobble, 64));
            CrossRecipeParallelScheduler old = new CrossRecipeParallelScheduler(3);
            old.setMaxSlots(3);
            old.setMaxVoltage(512);
            old.setTotalPowerBudget(512);
            stage(old, "a", batches.get(0), 10, 32L, 3);
            stage(old, "b", batches.get(1), 10, 64L, 6);
            stage(old, "paid", batches.get(2), 1, 128L, 1);
            NBTTagCompound state = work.serializeNBT();
            NBTTagCompound.class.getMethod("func_74757_a", String.class, boolean.class).invoke(state, "crossRecipeActive", true);
            NBTTagCompound.class.getMethod("func_74782_a", String.class, NBTBase.class)
                    .invoke(state, "crossRecipeScheduler", old.serializeNBT());
            NBTTagCompound.class.getMethod("func_74768_a", String.class, int.class).invoke(state, "Progress", 1);
            NBTTagCompound.class.getMethod("func_74768_a", String.class, int.class).invoke(state, "MaxProgress", Integer.MAX_VALUE);
            work.deserializeNBT(state);
            expectSlots(work, 4, 7);

            // Two simultaneous RUNNING slots need 96 EU. The third already earned its output.
            energy.removeEnergy(energy.getEnergyStored());
            energy.addEnergy(95);
            magic.drain(magic.getCapacity(), true);
            magic.fill(fuel.getFluid(20), true);
            work.updateWorkable();
            expectSlots(work, 4, 7);
            require(energy.getEnergyStored() == 95 && magic.getFluidAmount() == 20, "partial draw on insufficient EU");
            energy.addEnergy(2000 - energy.getEnergyStored());
            magic.drain(20, true);
            work.updateWorkable();
            expectSlots(work, 4, 7);
            require(energy.getEnergyStored() == 2000 && magic.getFluidAmount() == 0, "EU spent without magic");
            magic.fill(fuel.getFluid(20), true);
            work.updateWorkable();
            work.updateWorkable();
            expectSlots(work, 6, 9);
            work.setWorkingEnabled(false);
            work.updateWorkable();
            expectSlots(work, 6, 9);
            require(energy.getEnergyStored() == 1808 && magic.getFluidAmount() == 18, "incorrect two-tick debit");
            assertBlocked(output, cobble);
            System.out.println("GTQT_LEGACY_INFUSION_OK phase=create slots=3 running=2 completed=1 progress=6,9 "
                    + "euSpent=192 magicSpent=2 insufficientEUHeld=true missingMagicHeld=true disabled=true");
        } else {
            require("reload".equals(phase), "unexpected phase " + phase);
            require(!work.isWorkingEnabled(), "working switch lost on restart");
            expectSlots(work, 6, 9);
            require(energy.getEnergyStored() == 1808 && magic.getFluidAmount() == 18, "saved resources changed");
            assertBlocked(output, cobble);
            work.setWorkingEnabled(true);
            for (int i = 0; i < 5; i++) work.updateWorkable();
            List<RecipeSlot> complete = work.getCrossRecipeScheduler().getActiveSlots();
            require(complete.size() == 3 && complete.stream().allMatch(RecipeSlot::isCompleted),
                    "finished snapshots not retained with blocked output");
            require(energy.getEnergyStored() == 1520 && magic.getFluidAmount() == 13, "incorrect remaining slot costs");
            for (int i = 0; i < 3; i++) work.updateWorkable();
            require(energy.getEnergyStored() == 1520 && magic.getFluidAmount() == 13,
                    "completed slots drew resources while output was blocked");
            assertBlocked(output, cobble);
            energy.removeEnergy(energy.getEnergyStored());
            magic.drain(magic.getCapacity(), true);
            ItemStack empty = (ItemStack) ItemStack.class.getField("field_190927_a").get(null);
            for (int i = 0; i < output.getSlots(); i++) output.setStackInSlot(i, empty);
            for (int i = 0; i < 4; i++) work.updateWorkable();
            CrossRecipeParallelScheduler finished = work.getCrossRecipeScheduler();
            require(finished == null || !finished.hasActiveSlots(), "slot still active after delivery");
            int delivered = 0;
            for (int i = 0; i < output.getSlots(); i++) delivered += count(output.getStackInSlot(i));
            require(delivered == 3, "unexpected quantity delivered after reload " + delivered);
            for (int i = 0; i < 3; i++) {
                NBTTagCompound wanted = batches.get(i).output.serializeNBT();
                int matched = 0;
                for (int j = 0; j < output.getSlots(); j++) {
                    if (wanted.equals(output.getStackInSlot(j).serializeNBT())) matched++;
                }
                require(matched == 1, "lost, extra or changed saved output " + wanted);
            }
            System.out.println("GTQT_LEGACY_INFUSION_OK phase=reload slots=3 restoredProgress=6,9 "
                    + "euSpent=288 magicSpent=5 completedWhileBlocked=3 freeFlush=true delivered=3");
        }
        for (int i = 0; i < machine.getInputInventory().getSlots(); i++) {
            require(count(machine.getInputInventory().getStackInSlot(i)) == 0, "unexpected item input");
        }
        for (int i = 0; i < machine.getInputFluidInventory().getTanks(); i++) {
            require(machine.getInputFluidInventory().getTankAt(i).getFluidAmount() == 0, "unexpected aspect input");
        }
    }

    private static void stage(CrossRecipeParallelScheduler scheduler, String name, InfusionCases.Batch batch,
                              int duration, long eut, int paidTicks) {
        RecipeSlot slot = scheduler.acquireSlot();
        require(slot != null, "no spare legacy slot " + name);
        slot.startRecipe(batch.recipe, duration, eut, Collections.singletonList(batch.output), Collections.emptyList(),
                1, name);
        for (int i = 0; i < paidTicks; i++) slot.tick();
    }

    private static void expectSlots(MultiblockRecipeLogic work, int a, int b) {
        CrossRecipeParallelScheduler stored = work.getCrossRecipeScheduler();
        require(stored != null && stored.getActiveSlotCount() == 3, "unexpected stored slot count");
        for (RecipeSlot slot : stored.getActiveSlots()) {
            switch (slot.getRecipeDisplayName()) {
                case "a": require(slot.isRunning() && slot.getProgressTime() == a, "slot a " + slot); break;
                case "b": require(slot.isRunning() && slot.getProgressTime() == b, "slot b " + slot); break;
                case "paid": require(slot.isCompleted(), "slot paid " + slot); break;
                default: throw new IllegalStateException("unexpected saved slot " + slot);
            }
        }
    }

    private static void assertBlocked(IItemHandlerModifiable inventory, Item cobble) throws Exception {
        for (int i = 0; i < inventory.getSlots(); i++) {
            ItemStack stack = inventory.getStackInSlot(i);
            require(new ItemStack(cobble, 64).serializeNBT().equals(stack.serializeNBT()),
                    "output blocker unexpectedly changed at " + i);
        }
    }

    private static int count(ItemStack stack) throws ReflectiveOperationException {
        return (int) ItemStack.class.getMethod("func_190916_E").invoke(stack);
    }

    private static void require(boolean ok, String message) {
        if (!ok) throw new IllegalStateException("Legacy infusion recovery: " + message);
    }
}
