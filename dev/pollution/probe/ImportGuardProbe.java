package gtqtdev.probe;

import gregtech.api.recipes.Recipe;
import gregtech.api.recipes.RecipeMap;
import gregtech.api.unification.material.Material;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.item.crafting.Ingredient;
import net.minecraft.util.ResourceLocation;
import net.minecraftforge.fluids.FluidStack;
import net.minecraftforge.fml.common.registry.ForgeRegistries;
import net.minecraftforge.oredict.OreDictionary;
import thaumcraft.api.ThaumcraftApi;
import thaumcraft.api.aspects.Aspect;
import thaumcraft.api.aspects.AspectList;
import thaumcraft.api.crafting.IThaumcraftRecipe;
import thaumcraft.api.crafting.InfusionRecipe;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Server-only import checks. Any synthetic infusion is removed before the world continues ticking. */
public final class ImportGuardProbe {
    private static Set<Recipe> identities(Collection<Recipe> recipes) {
        Set<Recipe> result = Collections.newSetFromMap(new IdentityHashMap<>());
        result.addAll(recipes);
        return result;
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException("Infusion import guard: " + message);
    }

    private static ItemStack item(String name) {
        Item item = ForgeRegistries.ITEMS.getValue(new ResourceLocation("minecraft", name));
        require(item != null, "missing fixture item " + name);
        return new ItemStack(item);
    }

    private static ItemStack[] choices(Ingredient ingredient) throws Exception {
        return (ItemStack[]) Ingredient.class.getMethod("func_193365_a").invoke(ingredient);
    }

    private static Ingredient ingredient(ItemStack... stacks) throws Exception {
        return (Ingredient) Ingredient.class.getMethod("func_193369_a", ItemStack[].class).invoke(null, (Object) stacks);
    }

    private static boolean sameItem(ItemStack a, ItemStack b) throws Exception {
        return OreDictionary.itemMatches(a, b, true)
                && (Boolean) ItemStack.class.getMethod("func_77970_a", ItemStack.class, ItemStack.class).invoke(null, a, b);
    }

    private static String verifyRealAlternatives(RecipeMap<?> map) throws Exception {
        for (Map.Entry<ResourceLocation, IThaumcraftRecipe> entry : ThaumcraftApi.getCraftingRecipes().entrySet()) {
            if (!(entry.getValue() instanceof InfusionRecipe)) continue;
            InfusionRecipe source = (InfusionRecipe) entry.getValue();
            if (!(source.recipeOutput instanceof ItemStack) || source.getRecipeInput() == null) continue;
            ItemStack[] alternatives = choices(source.getRecipeInput());
            if (alternatives.length < 2) continue;
            List<ItemStack> items = new ArrayList<>();
            items.add(alternatives[0]);
            for (Ingredient input : source.getComponents()) {
                ItemStack[] stacks = choices(input);
                if (stacks.length == 0) break;
                items.add(stacks[0]);
            }
            if (items.size() != source.getComponents().size() + 1) continue;
            for (Recipe recipe : map.getRecipeList()) {
                if (!sameItem((ItemStack) source.recipeOutput, recipe.getOutputs().get(0))) continue;
                List<FluidStack> fluids = new ArrayList<>();
                recipe.getFluidInputs().forEach(in -> fluids.add(in.getInputFluidStack()));
                if (!recipe.matches(false, items, fluids)) continue;
                for (ItemStack candidate : alternatives) {
                    if (sameItem(alternatives[0], candidate)) continue;
                    items.set(0, candidate);
                    require(recipe.matches(false, items, fluids), entry.getKey() + " rejected a second central ingredient");
                    return entry.getKey().toString();
                }
            }
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    public static void verify() throws Exception {
        RecipeMap<?> map = (RecipeMap<?>) Class.forName("meowmel.pollution.api.recipes.PORecipeMaps")
                .getField("INDUSTRIAL_INFUSION_RECIPES").get(null);
        Method register = Class.forName("meowmel.pollution.api.recipes.builder.IndustrialInfusionBuilder")
                .getDeclaredMethod("register", ResourceLocation.class, InfusionRecipe.class, ItemStack.class);
        register.setAccessible(true);
        Map<Aspect, Material> mapping = (Map<Aspect, Material>) Class
                .forName("meowmel.pollution.api.utils.POAspectToGtFluidList").getField("aspectToGtFluidList").get(null);
        String original = verifyRealAlternatives(map);
        Set<Recipe> before = identities(map.getRecipeList());
        ItemStack first = item("record_13"), second = item("record_cat");
        ItemStack pedestal = item("command_block_minecart"), output = item("barrier");
        Ingredient center = ingredient(first, second);
        AspectList aspects = new AspectList().add(Aspect.AIR, 1);
        InfusionRecipe fixture = new InfusionRecipe("", output, 0, aspects, center, pedestal, pedestal);
        ResourceLocation id = new ResourceLocation("gtqtcompatprobe", "import_guard");
        try {
            // Negative cases run first so a too-permissive importer cannot be masked by recipe collisions.
            register.invoke(null, id, new InfusionRecipe("", output, 0, aspects, center, ingredient()), output);
            require(identities(map.getRecipeList()).equals(before), "empty pedestal produced a discounted recipe");
            Material air = mapping.get(Aspect.AIR);
            require(air != null, "fixture needs a real AIR mapping");
            mapping.remove(Aspect.AIR);
            try {
                register.invoke(null, id, fixture, output);
                require(identities(map.getRecipeList()).equals(before), "unmapped aspect produced a discounted recipe");
            } finally {
                mapping.put(Aspect.AIR, air);
            }
            register.invoke(null, id, fixture, output);
            Set<Recipe> added = identities(map.getRecipeList());
            added.removeAll(before);
            require(added.size() == 1, "expected one fixture recipe, got " + added.size());
            Recipe test = added.iterator().next();
            List<FluidStack> fluids = Collections.singletonList(air.getFluid(144));
            for (ItemStack candidate : Arrays.asList(first, second)) {
                List<ItemStack> full = Arrays.asList(candidate, pedestal, pedestal);
                require(map.findRecipe(480, full, fluids) == test, "lookup failed for one central alternative");
                require(!test.matches(false, Arrays.asList(candidate, pedestal), fluids), "accepted one pedestal instead of two");
            }
        } finally {
            for (Recipe entry : new ArrayList<>(map.getRecipeList())) {
                if (!before.contains(entry)) require(map.removeRecipe(entry), "could not remove test infusion");
            }
            require(identities(map.getRecipeList()).equals(before), "recipe map not restored");
        }
        System.out.println("GTQT_IMPORT_GUARD_OK centralCandidates=2 repeatedPedestals=2 emptyRejected=true"
                + " unmappedAspectRejected=true restored=true liveCentralRecipe=" + (original == null ? "fixture" : original));
    }
}
